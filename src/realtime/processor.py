"""
Процессор потокового аудио для real-time транскрипции

Обрабатывает аудио чанки и интегрируется с WhisperX для транскрипции.
"""

import asyncio
import logging
import numpy as np
from typing import Optional, List, Any
from datetime import datetime
import base64
import io

from .models import SessionConfig
from ..core.whisper_manager import WhisperManager

logger = logging.getLogger(__name__)


class AudioBuffer:
    """
    Буфер для накопления аудио данных
    """
    
    def __init__(self, sample_rate: int = 24000, max_duration_ms: int = 30000):
        """
        Инициализация буфера
        
        Args:
            sample_rate: Частота дискретизации
            max_duration_ms: Максимальная длительность буфера в мс (30 секунд)
        """
        self.sample_rate = sample_rate
        self.max_samples = int(sample_rate * max_duration_ms / 1000)
        self.buffer: List[float] = []
        self.total_samples = 0
        
    def add_chunk(self, audio_data: np.ndarray):
        """
        Добавить аудио чанк в буфер
        
        Args:
            audio_data: Аудио данные
        """
        # Конвертировать в список и добавить
        chunk_list = audio_data.flatten().tolist()
        self.buffer.extend(chunk_list)
        self.total_samples += len(chunk_list)
        
        # НЕ ограничиваем размер буфера - пусть накапливается до 30 секунд
    
    def get_audio_for_processing(self, min_duration_ms: int = 1000) -> Optional[np.ndarray]:
        """
        Получить аудио для обработки
        
        Args:
            min_duration_ms: Минимальная длительность для обработки
            
        Returns:
            Optional[np.ndarray]: Аудио данные или None
        """
        min_samples = int(self.sample_rate * min_duration_ms / 1000)
        
        if len(self.buffer) >= min_samples:
            # Возвращаем копию буфера как numpy array
            return np.array(self.buffer, dtype=np.float32)
        
        return None
    
    def clear(self):
        """Очистить буфер"""
        self.buffer.clear()
        self.total_samples = 0
    
    def get_duration_ms(self) -> int:
        """Получить длительность буфера в мс"""
        return int(len(self.buffer) * 1000 / self.sample_rate)
    
    def is_full_segment(self) -> bool:
        """Проверить, накопился ли полный 30-секундный сегмент"""
        return self.get_duration_ms() >= 30000


class StreamingAudioProcessor:
    """
    Процессор потокового аудио
    
    Накапливает аудио чанки и выполняет транскрипцию с помощью WhisperX.
    Логика: накапливаем 30 секунд, транскрибируем каждую секунду промежуточно, 
    через 30 секунд финальная транскрипция и переход к новому сегменту.
    """
    
    def __init__(self, config: SessionConfig, whisper_manager: WhisperManager):
        """
        Инициализация процессора
        
        Args:
            config: Конфигурация сессии
            whisper_manager: Менеджер WhisperX
        """
        self.config = config
        self.whisper_manager = whisper_manager
        self.audio_buffer = AudioBuffer(
            sample_rate=config.sample_rate,
            max_duration_ms=30000  # 30 секунд максимум
        )
        
        self.last_transcription = ""
        self.processing_lock = asyncio.Lock()
        self.chunks_received = 0
        self.last_processed_at = datetime.utcnow()
        
        # 30-секундные сегменты с промежуточной транскрипцией каждую секунду
        self.segment_start_time = datetime.utcnow()
        self.process_interval_ms = 1000      # Промежуточная транскрипция каждую секунду
        self.last_process_time = datetime.utcnow()
        self.current_segment_text = ""       # Текст текущего сегмента
        self.completed_segments = []         # Завершенные сегменты
        self.current_segment = 1             # Номер текущего сегмента
        
        logger.info(f"StreamingAudioProcessor initialized with 30s segments: {config}")
    
    async def process_chunk(self, audio_data: bytes, sequence: int) -> Optional[str]:
        """
        Обработать аудио чанк
        
        Args:
            audio_data: Аудио данные в формате bytes
            sequence: Порядковый номер чанка
            
        Returns:
            Optional[str]: Результат транскрипции или None
        """
        try:
            # Декодировать аудио данные
            audio_array = await self._decode_audio_data(audio_data)
            if audio_array is None:
                logger.error(f"Failed to decode audio data for sequence {sequence}")
                return None
            
            # Добавить в буфер
            self.audio_buffer.add_chunk(audio_array)
            self.chunks_received += 1
            
            # Проверить, заполнился ли буфер на 30 секунд
            if self.audio_buffer.is_full_segment():
                async with self.processing_lock:
                    # Финальная обработка 30-секундного сегмента
                    final_result = await self._process_final_segment()
                    if final_result:
                        # Сохранить сегмент и очистить буфер
                        self._save_segment_and_reset(final_result)
                        return final_result
            
            # Проверить, нужно ли делать промежуточную транскрипцию (каждую секунду)
            elif self._should_process():
                async with self.processing_lock:
                    result = await self._process_buffer_interim()
                    if result:
                        self.current_segment_text = result
                        self.last_processed_at = datetime.utcnow()
                        return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing audio chunk {sequence}: {e}")
            return None
    
    async def get_partial_result(self) -> Optional[str]:
        """
        Получить частичный результат транскрипции
        
        Returns:
            Optional[str]: Частичный результат
        """
        return self.current_segment_text if self.current_segment_text else None
    
    async def _decode_audio_data(self, audio_data: bytes) -> Optional[np.ndarray]:
        """
        Декодировать аудио данные
        
        Args:
            audio_data: Аудио данные в bytes
            
        Returns:
            Optional[np.ndarray]: Декодированные аудио данные
        """
        try:
            # Предполагаем, что данные приходят как PCM16
            # В реальной реализации может потребоваться более сложное декодирование
            
            # Конвертируем bytes в int16 array
            audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
            
            # Нормализуем в float32 [-1, 1]
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            return audio_float32
            
        except Exception as e:
            logger.error(f"Error decoding audio data: {e}")
            return None
    
    def _should_process(self) -> bool:
        """
        Определить, нужно ли делать промежуточную транскрипцию (каждую секунду)
        
        Returns:
            bool: True если нужно обрабатывать
        """
        buffer_duration = self.audio_buffer.get_duration_ms()
        time_since_last_process = (datetime.utcnow() - self.last_process_time).total_seconds() * 1000
        
        # Промежуточная транскрипция каждую секунду, если есть хоть какие-то данные
        return (
            time_since_last_process >= self.process_interval_ms and  # Каждую секунду
            buffer_duration >= 500  # Минимум 0.5 секунды
        )
    
    async def _process_buffer_interim(self) -> Optional[str]:
        """
        Промежуточная обработка буфера с помощью WhisperX (каждую секунду)
        
        Returns:
            Optional[str]: Результат транскрипции (накопленный текст текущего сегмента)
        """
        try:
            # Получить ВСЕ накопленные аудио данные текущего сегмента
            audio_data = self.audio_buffer.get_audio_for_processing(min_duration_ms=500)
            
            if audio_data is None or len(audio_data) == 0:
                return None
            
            current_duration = len(audio_data) * 1000 / self.config.sample_rate
            
            logger.debug(f"Interim processing segment {self.current_segment}: {current_duration:.1f}ms accumulated audio")
            
            # Вызов WhisperX для промежуточной транскрипции накопленного аудио
            result = await self.whisper_manager.transcribe_audio_chunk(
                audio_data=audio_data,
                sample_rate=self.config.sample_rate,
                language=self.config.language
            )
            
            if result:
                self.last_transcription = result
                self.last_process_time = datetime.utcnow()
                
                logger.debug(f"Segment {self.current_segment} interim transcription updated, text length: {len(result)} chars")
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error in interim processing of segment {self.current_segment}: {e}")
            return None
    
    async def _process_final_segment(self) -> Optional[str]:
        """
        Финальная обработка полного 30-секундного сегмента
        
        Returns:
            Optional[str]: Финальный результат транскрипции сегмента
        """
        try:
            # Получить ВСЕ аудио данные сегмента
            audio_data = self.audio_buffer.get_audio_for_processing(min_duration_ms=500)
            
            if audio_data is None or len(audio_data) == 0:
                return None
            
            current_duration = len(audio_data) * 1000 / self.config.sample_rate
            
            logger.info(f"Final processing of segment {self.current_segment}: {current_duration:.1f}ms total audio")
            
            # Финальная транскрипция всего 30-секундного сегмента
            result = await self.whisper_manager.transcribe_audio_chunk(
                audio_data=audio_data,
                sample_rate=self.config.sample_rate,
                language=self.config.language
            )
            
            if result:
                logger.info(f"Segment {self.current_segment} completed, text length: {len(result)} chars")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error in final processing of segment {self.current_segment}: {e}")
            return None
    
    def _save_segment_and_reset(self, final_text: str):
        """
        Сохранить завершенный сегмент и сбросить буфер для нового сегмента
        
        Args:
            final_text: Финальный текст сегмента
        """
        # Сохранить завершенный сегмент
        segment_data = {
            "segment": self.current_segment,
            "text": final_text,
            "completed_at": datetime.utcnow().isoformat(),
            "duration_ms": self.audio_buffer.get_duration_ms()
        }
        self.completed_segments.append(segment_data)
        
        logger.info(f"Segment {self.current_segment} saved and completed")
        
        # Очистить буфер и начать новый сегмент
        self.audio_buffer.clear()
        self.current_segment += 1
        self.current_segment_text = ""
        self.segment_start_time = datetime.utcnow()
        self.last_process_time = datetime.utcnow()
        
        logger.info(f"Started new segment {self.current_segment}")
    
    def get_full_accumulated_text(self) -> str:
        """
        Получить весь накопленный текст (все завершенные сегменты + текущий сегмент)
        
        Returns:
            str: Полный накопленный текст
        """
        full_text = ""
        
        # Добавить все завершенные сегменты
        for segment_data in self.completed_segments:
            if full_text:
                full_text += " "
            full_text += segment_data["text"]
        
        # Добавить текущий сегмент
        if self.current_segment_text:
            if full_text:
                full_text += " "
            full_text += self.current_segment_text
        
        return full_text

    async def cleanup(self):
        """
        Очистить ресурсы процессора
        """
        try:
            # Очистить буфер
            self.audio_buffer.clear()
            
            # Сбросить состояние
            self.last_transcription = ""
            self.chunks_received = 0
            self.current_segment_text = ""
            self.completed_segments.clear()
            self.current_segment = 1
            
            logger.info("StreamingAudioProcessor cleaned up")
            
        except Exception as e:
            logger.error(f"Error during processor cleanup: {e}")
    
    def get_stats(self) -> dict:
        """
        Получить статистику процессора
        
        Returns:
            dict: Статистика
        """
        time_since_last_process = (datetime.utcnow() - self.last_process_time).total_seconds() * 1000
        time_since_segment_start = (datetime.utcnow() - self.segment_start_time).total_seconds() * 1000
        
        return {
            "chunks_received": self.chunks_received,
            "buffer_duration_ms": self.audio_buffer.get_duration_ms(),
            "buffer_samples": len(self.audio_buffer.buffer),
            "last_transcription": self.current_segment_text[:50] + "..." if len(self.current_segment_text) > 50 else self.current_segment_text,
            "last_processed_at": self.last_processed_at.isoformat(),
            "segment_cycles": {
                "current_segment": self.current_segment,
                "time_in_current_segment_ms": int(time_since_segment_start),
                "time_since_last_process_ms": int(time_since_last_process),
                "next_process_in_ms": max(0, self.process_interval_ms - int(time_since_last_process)),
                "progress_to_segment_percent": min(100, int(time_since_segment_start / 30000 * 100)),
                "completed_segments_count": len(self.completed_segments),
                "current_text_length": len(self.current_segment_text)
            },
            "config": {
                "sample_rate": self.config.sample_rate,
                "buffer_size_ms": self.config.buffer_size_ms,
                "language": self.config.language,
                "model": self.config.model
            }
        } 
"""
Менеджер для работы с моделями WhisperX
"""
import os
import threading
import torch
import json
from typing import Optional, Callable, Dict, Any

import whisperx

from ..models.schemas import TranscriptionConfig
from ..utils import DependencyValidationError, validate_whisperx_dependencies
from .summarization_manager import SummarizationManager
from .diarization_manager import DiarizationManager
from .alignment_manager import AlignmentManager


class WhisperManager:
    """Менеджер для работы с моделями WhisperX"""
    
    def __init__(self):
        self.model = None
        self.models_loaded = False
        self.loading_lock = threading.Lock()
        self.device = self._detect_device()
        self.compute_type = self._detect_compute_type()
        
        # Инициализируем менеджеры
        self.summarization_manager = SummarizationManager(
            device=self.device,
            compute_type=self.compute_type
        )
        self.diarization_manager = DiarizationManager(
            device=self.device
        )
        self.alignment_manager = AlignmentManager(
            device=self.device
        )
        
        print(f"🔧 Обнаружено устройство: {self.device}, compute_type: {self.compute_type}")
    
    def _detect_device(self) -> str:
        """Определение доступного устройства"""
        if torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def _detect_compute_type(self) -> str:
        """Автоматическое определение compute_type"""
        if self.device == "cuda":
            # Проверяем поддержку float16 на GPU
            try:
                # Пробуем создать тензор float16 на GPU
                test_tensor = torch.tensor([1.0], dtype=torch.float16, device="cuda")
                return "float16"
            except Exception:
                return "float32"
        else:
            # Для CPU используем int8 для лучшей производительности
            return "int8"
    
    def load_models(self, config: TranscriptionConfig, status_callback: Optional[Callable] = None):
        """Загрузка моделей WhisperX в память"""
        with self.loading_lock:
            if self.models_loaded:
                return

            try:
                validate_whisperx_dependencies()
            except DependencyValidationError as dep_error:
                error_message = str(dep_error)
                print(f"❌ Ошибка проверки зависимостей WhisperX: {error_message}")
                if status_callback:
                    status_callback("dependency_error", error_message, 0)
                raise RuntimeError(error_message) from dep_error
            
            # Определяем compute_type
            compute_type = config.compute_type
            if compute_type == "auto":
                compute_type = self.compute_type
                print(f"🔧 Автоматически выбран compute_type: {compute_type}")
            
            if status_callback:
                status_callback("loading_whisper_model", "Загрузка модели Whisper...", 20)
            print(f"🔧 Загрузка модели Whisper: {config.model}")
            self.model = whisperx.load_model(
                config.model, 
                self.device, 
                compute_type=compute_type
            )
            
            # Загружаем модель выравнивания
            self.alignment_manager.load_model(
                language=config.language,
                status_callback=status_callback
            )
            
            # Загружаем модель диаризации если нужно
            if config.diarize and config.hf_token:
                self.diarization_manager.load_model(
                    hf_token=config.hf_token,
                    status_callback=status_callback
                )
            
            self.models_loaded = True
            print("✅ Модели загружены успешно!")
    
    def load_summarization_model(self, model_name: str = None, status_callback: Optional[Callable] = None):
        """Загрузка модели суммаризации через SummarizationManager"""
        self.summarization_manager.load_model(model_name=model_name, status_callback=status_callback)
    
    def create_summary(self, transcription_result: dict, status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Создание суммаризации транскрипции через SummarizationManager
        
        Args:
            transcription_result: Результат транскрипции с сегментами
            status_callback: Callback для обновления статуса
            
        Returns:
            Словарь с суммаризацией
        """
        return self.summarization_manager.create_summary(transcription_result, status_callback)
    

    
    def transcribe_audio(self, audio_path: str, config: TranscriptionConfig, status_callback: Optional[Callable] = None) -> dict:
        """
        Выполнение транскрипции аудио
        
        Args:
            audio_path: Путь к аудио файлу
            config: Конфигурация транскрипции
            status_callback: Callback для обновления статуса
        
        Returns:
            Результат транскрипции
        """
        if not self.models_loaded:
            self.load_models(config, status_callback)
        
        # Загружаем аудио
        if status_callback:
            status_callback("loading_audio", "Загрузка аудио файла...", 32)
        print(f"🎵 Загрузка аудио файла: {audio_path}")
        audio = whisperx.load_audio(audio_path)
        
        # Транскрипция
        if status_callback:
            status_callback("transcribing", "Выполнение транскрипции...", 45)
        print(f"🎯 Выполнение транскрипции (язык: {config.language})...")
        result = self.model.transcribe(audio, batch_size=config.batch_size, language=config.language)
        
        # Выравнивание
        if self.alignment_manager.is_loaded:
            result = self.alignment_manager.align(
                result["segments"], 
                audio,
                status_callback
            )
        
        # Диаризация (если включена)
        if config.diarize and self.diarization_manager.is_loaded:
            if status_callback:
                status_callback("diarizing", "Диаризация спикеров...", 72)
            diarize_segments = self.diarization_manager.diarize(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)
        
        return result
    
    async def transcribe_audio_chunk(self, audio_data, sample_rate: int = 16000, language: str = "ru") -> str:
        """
        Транскрипция аудио чанка для real-time режима
        
        Args:
            audio_data: Numpy array с аудио данными
            sample_rate: Частота дискретизации
            language: Язык для транскрипции
            
        Returns:
            str: Результат транскрипции
        """
        if not self.models_loaded:
            # Для real-time нужно загрузить базовую конфигурацию
            from ..models.schemas import TranscriptionConfig
            basic_config = TranscriptionConfig(
                model="base",
                language=language,
                compute_type="auto",
                batch_size=16,
                diarize=False,
                hf_token=""
            )
            self.load_models(basic_config)
        
        try:
            # Убеждаемся, что audio_data - это numpy array float32
            import numpy as np
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data, dtype=np.float32)
            elif audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # WhisperX ожидает аудио с частотой 16kHz, нужно ресемплировать если нужно
            if sample_rate != 16000:
                # Простое ресемплирование (в продакшене лучше использовать librosa)
                import scipy.signal
                target_length = int(len(audio_data) * 16000 / sample_rate)
                audio_data = scipy.signal.resample(audio_data, target_length)
            
            # Транскрибируем аудио чанк
            result = self.model.transcribe(audio_data, batch_size=1)
            
            # Извлекаем текст из результата
            if result and "segments" in result and result["segments"]:
                text_parts = []
                for segment in result["segments"]:
                    if "text" in segment:
                        text_parts.append(segment["text"].strip())
                
                return " ".join(text_parts).strip()
            
            return ""
            
        except Exception as e:
            print(f"❌ Ошибка транскрипции чанка: {e}")
            return ""
    
    @property
    def is_loaded(self) -> bool:
        """Проверка загружены ли модели"""
        return self.models_loaded 
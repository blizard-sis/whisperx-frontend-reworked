"""
Менеджер real-time транскрипции

Управляет сессиями real-time транскрипции и интегрируется с существующим WhisperX.
"""

import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime

from .models import (
    SessionConfig, SessionStatus, create_session_id,
    create_transcription_partial, create_transcription_final,
    create_error_event
)
from ..core.whisper_manager import WhisperManager
from .processor import StreamingAudioProcessor

logger = logging.getLogger(__name__)


class RealtimeTranscriptionManager:
    """
    Менеджер real-time транскрипции
    
    Управляет активными сессиями, интегрируется с существующим WhisperManager
    и координирует потоковую обработку аудио.
    """
    
    def __init__(self, whisper_manager: Optional[WhisperManager] = None):
        """
        Инициализация менеджера
        
        Args:
            whisper_manager: Существующий WhisperManager или None для создания нового
        """
        self.whisper_manager = whisper_manager or WhisperManager()
        self.active_sessions: Dict[str, SessionStatus] = {}
        self.processors: Dict[str, StreamingAudioProcessor] = {}
        self.max_sessions = 10  # Максимальное количество одновременных сессий
        
        logger.info("RealtimeTranscriptionManager initialized")
    
    async def start_session(self, config: SessionConfig) -> str:
        """
        Начать новую сессию real-time транскрипции
        
        Args:
            config: Конфигурация сессии
            
        Returns:
            str: ID созданной сессии
            
        Raises:
            RuntimeError: Если превышено максимальное количество сессий
        """
        if len(self.active_sessions) >= self.max_sessions:
            raise RuntimeError(f"Maximum sessions limit reached: {self.max_sessions}")
        
        session_id = create_session_id()
        
        # Создать статус сессии
        session_status = SessionStatus(
            session_id=session_id,
            is_active=True,
            start_time=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            config=config,
            stats={
                "chunks_processed": 0,
                "total_duration_ms": 0,
                "avg_confidence": 0.0,
                "errors_count": 0
            }
        )
        
        # Создать процессор для сессии
        processor = StreamingAudioProcessor(
            config=config,
            whisper_manager=self.whisper_manager
        )
        
        # Сохранить сессию
        self.active_sessions[session_id] = session_status
        self.processors[session_id] = processor
        
        logger.info(f"Started realtime session: {session_id}")
        return session_id
    
    async def stop_session(self, session_id: str) -> bool:
        """
        Остановить сессию real-time транскрипции
        
        Args:
            session_id: ID сессии
            
        Returns:
            bool: True если сессия была остановлена, False если не найдена
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return False
        
        # Остановить процессор
        if session_id in self.processors:
            await self.processors[session_id].cleanup()
            del self.processors[session_id]
        
        # Обновить статус
        self.active_sessions[session_id].is_active = False
        
        # Удалить из активных сессий
        del self.active_sessions[session_id]
        
        logger.info(f"Stopped realtime session: {session_id}")
        return True
    
    async def process_audio_chunk(self, session_id: str, audio_data: bytes, sequence: int) -> Optional[str]:
        """
        Обработать аудио чанк для сессии
        
        Args:
            session_id: ID сессии
            audio_data: Аудио данные
            sequence: Порядковый номер чанка
            
        Returns:
            Optional[str]: Результат транскрипции или None
        """
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return None
        
        if session_id not in self.processors:
            logger.error(f"Processor not found for session: {session_id}")
            return None
        
        try:
            # Обновить время последней активности
            self.active_sessions[session_id].last_activity = datetime.utcnow()
            
            # Обработать чанк
            processor = self.processors[session_id]
            result = await processor.process_chunk(audio_data, sequence)
            
            # Обновить статистику
            stats = self.active_sessions[session_id].stats
            stats["chunks_processed"] += 1
            stats["total_duration_ms"] += 100  # Предполагаем 100ms чанки
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio chunk for session {session_id}: {e}")
            
            # Обновить статистику ошибок
            self.active_sessions[session_id].stats["errors_count"] += 1
            
            return None
    
    async def get_partial_result(self, session_id: str) -> Optional[str]:
        """
        Получить частичный результат транскрипции
        
        Args:
            session_id: ID сессии
            
        Returns:
            Optional[str]: Частичный результат или None
        """
        if session_id not in self.processors:
            return None
            
        try:
            processor = self.processors[session_id]
            return await processor.get_partial_result()
        except Exception as e:
            logger.error(f"Error getting partial result for session {session_id}: {e}")
            return None
    
    def get_session_status(self, session_id: str) -> Optional[SessionStatus]:
        """
        Получить статус сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Optional[SessionStatus]: Статус сессии или None
        """
        return self.active_sessions.get(session_id)
    
    def get_active_sessions(self) -> List[str]:
        """
        Получить список активных сессий
        
        Returns:
            List[str]: Список ID активных сессий
        """
        return list(self.active_sessions.keys())
    
    async def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """
        Очистить неактивные сессии
        
        Args:
            timeout_minutes: Таймаут неактивности в минутах
        """
        current_time = datetime.utcnow()
        inactive_sessions = []
        
        for session_id, status in self.active_sessions.items():
            inactive_duration = (current_time - status.last_activity).total_seconds() / 60
            if inactive_duration > timeout_minutes:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            logger.info(f"Cleaning up inactive session: {session_id}")
            await self.stop_session(session_id)
    
    async def get_system_stats(self) -> Dict[str, any]:
        """
        Получить системную статистику
        
        Returns:
            Dict: Статистика системы
        """
        total_chunks = sum(s.stats.get("chunks_processed", 0) for s in self.active_sessions.values())
        total_errors = sum(s.stats.get("errors_count", 0) for s in self.active_sessions.values())
        
        return {
            "active_sessions": len(self.active_sessions),
            "max_sessions": self.max_sessions,
            "total_chunks_processed": total_chunks,
            "total_errors": total_errors,
            "whisper_model_loaded": self.whisper_manager.model is not None if self.whisper_manager else False
        } 
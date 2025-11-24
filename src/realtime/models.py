"""
Pydantic модели для real-time транскрипции
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


class RealtimeEventType(str, Enum):
    """Типы событий real-time транскрипции"""
    SESSION_START = "session.start"
    SESSION_STOP = "session.stop"
    AUDIO_CHUNK = "audio.chunk"
    TRANSCRIPTION_PARTIAL = "transcription.partial"
    TRANSCRIPTION_FINAL = "transcription.final"
    ERROR = "error"
    STATUS = "status"


class SessionConfig(BaseModel):
    """Конфигурация сессии транскрипции"""
    language: str = Field(default="ru", description="Язык транскрипции")
    model: str = Field(default="large-v3", description="Модель WhisperX")
    sample_rate: int = Field(default=24000, description="Частота дискретизации")
    chunk_size_ms: int = Field(default=500, description="Размер чанка в мс")
    buffer_size_ms: int = Field(default=5000, description="Размер буфера в мс")
    enable_vad: bool = Field(default=True, description="Включить Voice Activity Detection")
    diarization: bool = Field(default=False, description="Включить диаризацию")


class RealtimeEvent(BaseModel):
    """Базовое событие real-time"""
    type: RealtimeEventType
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None


class SessionStartEvent(RealtimeEvent):
    """Событие начала сессии"""
    type: RealtimeEventType = RealtimeEventType.SESSION_START
    config: SessionConfig


class AudioChunkEvent(RealtimeEvent):
    """Событие аудио чанка"""
    type: RealtimeEventType = RealtimeEventType.AUDIO_CHUNK
    audio_data: str = Field(..., description="Base64 encoded audio data")
    sequence: int = Field(..., description="Порядковый номер чанка")
    duration_ms: int = Field(..., description="Длительность чанка в мс")


class TranscriptionResult(BaseModel):
    """Результат транскрипции"""
    text: str = Field(..., description="Транскрибированный текст")
    confidence: float = Field(ge=0.0, le=1.0, description="Уверенность модели")
    start_time: Optional[float] = Field(None, description="Время начала в секундах")
    end_time: Optional[float] = Field(None, description="Время окончания в секундах")
    is_final: bool = Field(default=False, description="Финальный результат")
    window_info: Optional[Dict[str, Any]] = Field(None, description="Информация о скользящем окне")


class TranscriptionPartialEvent(RealtimeEvent):
    """Событие частичной транскрипции"""
    type: RealtimeEventType = RealtimeEventType.TRANSCRIPTION_PARTIAL
    result: TranscriptionResult


class TranscriptionFinalEvent(RealtimeEvent):
    """Событие финальной транскрипции"""
    type: RealtimeEventType = RealtimeEventType.TRANSCRIPTION_FINAL
    result: TranscriptionResult


class ErrorEvent(RealtimeEvent):
    """Событие ошибки"""
    type: RealtimeEventType = RealtimeEventType.ERROR
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


class SessionStatus(BaseModel):
    """Статус сессии"""
    session_id: str
    is_active: bool
    start_time: datetime
    last_activity: datetime
    config: SessionConfig
    stats: Dict[str, Any] = Field(default_factory=dict)


class StatusEvent(RealtimeEvent):
    """Событие статуса"""
    type: RealtimeEventType = RealtimeEventType.STATUS
    status: SessionStatus


# Утилиты для создания событий
def create_session_id() -> str:
    """Создать уникальный ID сессии"""
    return f"rt_{uuid.uuid4().hex[:12]}"


def create_transcription_partial(
    session_id: str,
    text: str,
    confidence: float,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> TranscriptionPartialEvent:
    """Создать событие частичной транскрипции"""
    result = TranscriptionResult(
        text=text,
        confidence=confidence,
        start_time=start_time,
        end_time=end_time,
        is_final=False
    )
    return TranscriptionPartialEvent(session_id=session_id, result=result)


def create_transcription_final(
    session_id: str,
    text: str,
    confidence: float,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> TranscriptionFinalEvent:
    """Создать событие финальной транскрипции"""
    result = TranscriptionResult(
        text=text,
        confidence=confidence,
        start_time=start_time,
        end_time=end_time,
        is_final=True
    )
    return TranscriptionFinalEvent(session_id=session_id, result=result)


def create_error_event(
    session_id: str,
    error_code: str,
    error_message: str,
    details: Optional[Dict[str, Any]] = None
) -> ErrorEvent:
    """Создать событие ошибки"""
    return ErrorEvent(
        session_id=session_id,
        error_code=error_code,
        error_message=error_message,
        details=details
    ) 
"""
Модели данных для API
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class TranscriptionConfig(BaseModel):
    """Конфигурация для транскрипции"""
    model: str = "large-v3"  # Самая точная модель
    language: str = "ru"
    diarize: bool = True  # Диаризация включена по умолчанию
    hf_token: Optional[str] = None
    compute_type: str = "float32"  # Максимальная точность
    batch_size: int = 4  # Меньше батч = выше качество


class TranscriptionStatus(BaseModel):
    """Статус транскрипции"""
    id: str
    status: str  # pending, processing, completed, failed
    filename: str
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[str] = None
    progress_percent: Optional[int] = None


class TranscriptionResult(BaseModel):
    """Результат транскрипции"""
    id: str
    filename: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    transcript_file: Optional[str] = None
    audio_file: Optional[str] = None
    subtitle_files: Optional[Dict[str, str]] = None
    s3_links: Optional[Dict[str, str]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[str] = None
    progress_percent: Optional[int] = None


class TranscriptionListItem(BaseModel):
    """Элемент списка транскрипций"""
    id: str
    filename: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    transcript_file: Optional[str] = None
    audio_file: Optional[str] = None
    subtitle_files: Optional[Dict[str, str]] = None
    s3_links: Optional[Dict[str, str]] = None
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[str] = None
    progress_percent: Optional[int] = None
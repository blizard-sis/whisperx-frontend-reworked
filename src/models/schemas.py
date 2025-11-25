"""
Модели данных для API
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class TranscriptionConfig(BaseModel):
    """Конфигурация для транскрипции"""
    model: str = "large-v3"
    language: str = "ru"
    diarize: bool = True
    hf_token: Optional[str] = None
    batch_size: int = 4


class TranscriptionStatus(BaseModel):
    """Статус транскрипции"""
    id: str
    status: str
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
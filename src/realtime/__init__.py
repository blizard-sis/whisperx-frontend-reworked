"""
whisperx-fronted-docker-compose Real-Time Transcription Module

Модуль для real-time транскрипции аудио потоков.
Интегрируется с существующей WhisperX инфраструктурой.
"""

__version__ = "0.1.0"
__author__ = "whisperx-fronted-docker-compose Team"

from .manager import RealtimeTranscriptionManager
from .processor import StreamingAudioProcessor
from .websocket_handler import RealtimeWebSocketHandler

__all__ = [
    "RealtimeTranscriptionManager",
    "StreamingAudioProcessor", 
    "RealtimeWebSocketHandler"
] 
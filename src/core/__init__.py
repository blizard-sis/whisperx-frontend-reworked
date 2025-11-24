"""
Core модули для обработки транскрипции
"""

from .whisper_manager import WhisperManager
from .summarization_manager import SummarizationManager
from .transcription_processor import TranscriptionProcessor

__all__ = [
    'WhisperManager',
    'SummarizationManager', 
    'TranscriptionProcessor'
] 
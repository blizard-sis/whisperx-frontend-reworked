"""
Core модули для обработки транскрипции
"""

from .whisper_manager import WhisperManager
from .alignment_manager import AlignmentManager
from .diarization_manager import DiarizationManager
from .summarization_manager import SummarizationManager
from .transcription_processor import TranscriptionProcessor

__all__ = [
    'WhisperManager',
    'AlignmentManager',
    'DiarizationManager',
    'SummarizationManager',
    'TranscriptionProcessor'
] 
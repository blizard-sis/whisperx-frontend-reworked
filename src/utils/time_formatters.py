"""
Утилиты для форматирования времени в различных форматах субтитров
"""


def format_time_srt(seconds: float) -> str:
    """Форматирование времени для SRT"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_time_vtt(seconds: float) -> str:
    """Форматирование времени для VTT"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def format_time_tsv(seconds: float) -> str:
    """Форматирование времени для TSV (в секундах с тремя знаками после запятой)"""
    return f"{seconds:.3f}" 
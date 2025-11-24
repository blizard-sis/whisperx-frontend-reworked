"""
Конфигурация приложения
"""
import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
TEMP_DIR = DATA_DIR / "temp"
DATABASE_FILE = DATA_DIR / "transcriptions_db.json"

# Создаем директории
for dir_path in [DATA_DIR, UPLOADS_DIR, TRANSCRIPTS_DIR, TEMP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Поддерживаемые форматы
SUPPORTED_FORMATS = {
    # Аудио
    'mp3', 'm4a', 'wav', 'flac', 'ogg', 'wma', 'aac', 'opus',
    # Видео
    'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', '3gp', 'mts'
}

# Настройки сервера
SERVER_CONFIG = {
    'host': '0.0.0.0',
    'port': 8880,
    'reload': False,
    'log_level': 'info'
}

# CORS настройки
CORS_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:8880",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    "http://localhost:8880",
    "http://127.0.0.1:8880",
    "*"
]

# Настройки обработки
# 🎯 Максимальное качество (требует больше GPU памяти и времени)
PROCESSING_CONFIG = {
    'max_workers': 2,
    'default_model': 'large-v3',
    'default_language': 'ru',
    'default_compute_type': 'float16',
    'default_batch_size': 4,
    'default_diarize': True
} 
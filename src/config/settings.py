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
    "*"
]

# Настройки обработки транскрипции
# Все настройки моделей, языков и параметров обработки собраны здесь
# Используются в: TranscriptionProcessor, WhisperManager, SummarizationManager
PROCESSING_CONFIG = {
    'max_workers': 4,                                  # Количество параллельных задач транскрипции
    'whisperx_model': 'large-v3',                      # Модель Whisper (tiny/base/small/medium/large-v3)
    'whisperx_language': 'ru',                         # Язык транскрипции по умолчанию
    'whisperx_batch_size': 4,                          # Размер батча (меньше = качественнее, но медленнее)
    'default_diarize': True,                           # Включить диаризацию (разделение по спикерам) по умолчанию
    'summarization_model': 'Qwen/Qwen3-30B-A3B-Instruct-2507', # Модель для суммаризации текста
    'device_type': 'cuda',                             # Устройство для вычислений
    'compute_type': 'float16'                          # Тип вычислений (float16 для GPU, int8 для CPU)
}

# Секретные ключи (загружаются из .env)
HF_TOKEN = os.getenv('HF_TOKEN')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') 
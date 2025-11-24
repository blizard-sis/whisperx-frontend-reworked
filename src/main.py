"""
Главный файл приложения FastAPI
whisperx-fronted-docker-compose - AI Транскрипция

Основано на WhisperX by Max Bain (https://github.com/m-bain/whisperX)
Лицензия WhisperX: BSD-2-Clause
"""
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Загрузка переменных окружения из .env файла
load_dotenv()

from .api.routes import router
from .api.realtime_routes import router as realtime_router, initialize_realtime_system, shutdown_realtime_system  # Real-time маршруты
from .config.settings import CORS_ORIGINS


def create_app() -> FastAPI:
    """Создание и настройка FastAPI приложения"""
    
    app = FastAPI(
        title="whisperx-fronted-docker-compose - AI Транскрипция",
        description="API для транскрипции аудио и видео файлов с экспортом в 6 форматов и локальным хранением результатов.",
        version="2.1.0"
    )
    
    # Добавляем CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"]
    )
    
    # Подключаем роуты
    app.include_router(router, prefix="/api", tags=["Транскрипция"])
    app.include_router(realtime_router, prefix="/api", tags=["Real-Time Транскрипция"])  # Real-time маршруты
    
    @app.on_event("startup")
    async def startup_event():
        """Инициализация при запуске"""
        import os
        
        print("🚀 Запуск whisperx-fronted-docker-compose - AI Транскрипция v2.1...")
        print("\n" + "="*60)
        print("📋 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ:")
        print("="*60)
        
        # Важные переменные
        env_vars = {
            'CUDA_VISIBLE_DEVICES': os.getenv('CUDA_VISIBLE_DEVICES', 'НЕ УСТАНОВЛЕНА'),
            'HF_TOKEN': f"{os.getenv('HF_TOKEN', 'НЕ УСТАНОВЛЕНА')[:10]}..." if os.getenv('HF_TOKEN') else 'НЕ УСТАНОВЛЕНА',
            'WHISPERX_MODEL': os.getenv('WHISPERX_MODEL', 'large-v3 (по умолчанию)'),
            'WHISPERX_LANGUAGE': os.getenv('WHISPERX_LANGUAGE', 'ru (по умолчанию)'),
            'WHISPERX_BATCH_SIZE': os.getenv('WHISPERX_BATCH_SIZE', '16 (по умолчанию)'),
            'WHISPERX_COMPUTE_TYPE': os.getenv('WHISPERX_COMPUTE_TYPE', 'float16 (по умолчанию)'),
            'SUMMARIZATION_API_URL': os.getenv('SUMMARIZATION_API_URL', 'НЕ УСТАНОВЛЕНА'),
            'SUMMARIZATION_MODEL': os.getenv('SUMMARIZATION_MODEL', 'НЕ УСТАНОВЛЕНА'),
            'LD_LIBRARY_PATH': os.getenv('LD_LIBRARY_PATH', 'НЕ УСТАНОВЛЕНА')[:100] + '...' if os.getenv('LD_LIBRARY_PATH') and len(os.getenv('LD_LIBRARY_PATH', '')) > 100 else os.getenv('LD_LIBRARY_PATH', 'НЕ УСТАНОВЛЕНА'),
        }
        
        for key, value in env_vars.items():
            print(f"  {key}: {value}")
        
        print("="*60 + "\n")
        
        print("🌐 CORS настроен для всех доменов")
        print("📋 Доступные форматы экспорта: JSON, SRT, VTT, TSV, DOCX, PDF")
        print("💾 Локальное хранение файлов транскрипции")
        print("📂 Файлы доступны через API без внешних сервисов")
        print("💾 JSON база данных для метаданных транскрипций")
        print("🎙️ Real-time транскрипция включена (WebSocket: /api/realtime/ws)")
        
        # Инициализация real-time системы
        try:
            await initialize_realtime_system()
            print("✅ Real-time система инициализирована")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации real-time системы: {e}")
        
        print("✅ Сервер готов к работе! Модели будут загружены при первом запросе.")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Очистка ресурсов при остановке"""
        print("🔄 Остановка сервера...")
        try:
            await shutdown_realtime_system()
            print("✅ Real-time система остановлена")
        except Exception as e:
            print(f"⚠️ Ошибка остановки real-time системы: {e}")
        print("👋 Сервер остановлен")
    
    return app


# Создаем экземпляр приложения
app = create_app() 
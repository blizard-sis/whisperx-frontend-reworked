"""
API маршруты для real-time транскрипции

Содержит WebSocket эндпоинт и дополнительные HTTP маршруты для управления real-time сессиями.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..realtime.websocket_handler import RealtimeWebSocketHandler
from ..realtime.manager import RealtimeTranscriptionManager
from ..realtime.models import SessionConfig, SessionStatus
from ..core.whisper_manager import WhisperManager

logger = logging.getLogger(__name__)

# Создаем роутер для real-time API
router = APIRouter(prefix="/realtime", tags=["Real-Time Transcription"])

# Глобальные экземпляры (будут инициализированы при старте приложения)
realtime_manager: Optional[RealtimeTranscriptionManager] = None
websocket_handler: Optional[RealtimeWebSocketHandler] = None


def get_realtime_manager() -> RealtimeTranscriptionManager:
    """
    Получить экземпляр менеджера real-time транскрипции
    
    Returns:
        RealtimeTranscriptionManager: Менеджер транскрипции
    """
    global realtime_manager
    if realtime_manager is None:
        # Инициализация при первом обращении
        realtime_manager = RealtimeTranscriptionManager()
        logger.info("RealtimeTranscriptionManager initialized")
    return realtime_manager


def get_websocket_handler() -> RealtimeWebSocketHandler:
    """
    Получить экземпляр WebSocket обработчика
    
    Returns:
        RealtimeWebSocketHandler: WebSocket обработчик
    """
    global websocket_handler
    if websocket_handler is None:
        # Инициализация при первом обращении
        manager = get_realtime_manager()
        websocket_handler = RealtimeWebSocketHandler(manager)
        logger.info("RealtimeWebSocketHandler initialized")
    return websocket_handler


@router.websocket("/ws")
async def realtime_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket эндпоинт для real-time транскрипции
    
    Принимает WebSocket соединения и обрабатывает события real-time транскрипции:
    - session.start - начать сессию транскрипции
    - audio.chunk - отправить аудио чанк
    - session.stop - остановить сессию
    - ping - проверка соединения
    
    Args:
        websocket: WebSocket соединение
    """
    handler = get_websocket_handler()
    await handler.handle_connection(websocket)


@router.get("/status")
async def get_realtime_status():
    """
    Получить статус real-time системы
    
    Returns:
        dict: Статус системы
    """
    try:
        manager = get_realtime_manager()
        handler = get_websocket_handler()
        
        # Получить статистику
        system_stats = await manager.get_system_stats()
        connection_stats = handler.get_connection_stats()
        
        return {
            "status": "online",
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_stats,
            "connections": connection_stats,
            "version": "0.1.0"
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_active_sessions(manager: RealtimeTranscriptionManager = Depends(get_realtime_manager)):
    """
    Получить список активных сессий
    
    Returns:
        dict: Список активных сессий
    """
    try:
        active_sessions = manager.get_active_sessions()
        
        # Получить детальную информацию о каждой сессии
        sessions_info = []
        for session_id in active_sessions:
            status = manager.get_session_status(session_id)
            if status:
                sessions_info.append({
                    "session_id": session_id,
                    "is_active": status.is_active,
                    "start_time": status.start_time.isoformat(),
                    "last_activity": status.last_activity.isoformat(),
                    "config": status.config.dict(),
                    "stats": status.stats
                })
        
        return {
            "active_sessions_count": len(active_sessions),
            "sessions": sessions_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session_info(
    session_id: str,
    manager: RealtimeTranscriptionManager = Depends(get_realtime_manager)
):
    """
    Получить информацию о конкретной сессии
    
    Args:
        session_id: ID сессии
        
    Returns:
        dict: Информация о сессии
    """
    try:
        status = manager.get_session_status(session_id)
        if not status:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "is_active": status.is_active,
            "start_time": status.start_time.isoformat(),
            "last_activity": status.last_activity.isoformat(),
            "config": status.config.dict(),
            "stats": status.stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def stop_session(
    session_id: str,
    manager: RealtimeTranscriptionManager = Depends(get_realtime_manager)
):
    """
    Остановить сессию транскрипции
    
    Args:
        session_id: ID сессии
        
    Returns:
        dict: Результат операции
    """
    try:
        success = await manager.stop_session(session_id)
        
        if success:
            return {
                "success": True,
                "message": f"Session {session_id} stopped successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/cleanup")
async def cleanup_inactive_sessions(
    timeout_minutes: int = 30,
    manager: RealtimeTranscriptionManager = Depends(get_realtime_manager)
):
    """
    Очистить неактивные сессии
    
    Args:
        timeout_minutes: Таймаут неактивности в минутах (по умолчанию 30)
        
    Returns:
        dict: Результат очистки
    """
    try:
        # Получить список сессий до очистки
        sessions_before = len(manager.get_active_sessions())
        
        # Выполнить очистку
        await manager.cleanup_inactive_sessions(timeout_minutes)
        
        # Получить список сессий после очистки
        sessions_after = len(manager.get_active_sessions())
        cleaned_count = sessions_before - sessions_after
        
        return {
            "success": True,
            "cleaned_sessions": cleaned_count,
            "active_sessions_before": sessions_before,
            "active_sessions_after": sessions_after,
            "timeout_minutes": timeout_minutes,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_realtime_config():
    """
    Получить конфигурацию real-time системы
    
    Returns:
        dict: Конфигурация системы
    """
    try:
        # Возвращаем конфигурацию по умолчанию
        default_config = SessionConfig()
        
        return {
            "default_config": default_config.dict(),
            "supported_languages": ["ru", "en", "es", "fr", "de", "it", "pt", "pl", "tr", "nl"],
            "supported_models": ["large-v3", "large-v2", "medium", "small", "base"],
            "audio_requirements": {
                "sample_rate": 24000,
                "channels": 1,
                "format": "PCM16",
                "chunk_size_ms": [50, 100, 200, 500],
                "buffer_size_ms": [500, 1000, 2000, 3000]
            },
            "limits": {
                "max_sessions": 10,
                "max_session_duration_hours": 24,
                "max_chunk_size_bytes": 8192
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Проверка здоровья real-time сервиса
    
    Returns:
        dict: Статус здоровья
    """
    try:
        manager = get_realtime_manager()
        handler = get_websocket_handler()
        
        # Проверить состояние компонентов
        whisper_available = manager.whisper_manager.model is not None if manager.whisper_manager else False
        
        health_status = {
            "status": "healthy",
            "components": {
                "realtime_manager": "online",
                "websocket_handler": "online",
                "whisper_manager": "online" if whisper_available else "not_loaded"
            },
            "active_sessions": len(manager.get_active_sessions()),
            "active_connections": handler.get_active_connections_count(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Определить общий статус
        if not whisper_available:
            health_status["status"] = "degraded"
            health_status["warnings"] = ["WhisperX model not loaded"]
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Функция для инициализации real-time системы (вызывается при старте приложения)
async def initialize_realtime_system(whisper_manager: Optional[WhisperManager] = None):
    """
    Инициализировать real-time систему
    
    Args:
        whisper_manager: Существующий WhisperManager для переиспользования
    """
    global realtime_manager, websocket_handler
    
    try:
        # Создать менеджер с существующим WhisperManager если передан
        realtime_manager = RealtimeTranscriptionManager(whisper_manager)
        
        # Создать WebSocket обработчик
        websocket_handler = RealtimeWebSocketHandler(realtime_manager)
        
        logger.info("Real-time transcription system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize real-time system: {e}")
        raise


# Функция для остановки real-time системы (вызывается при остановке приложения)
async def shutdown_realtime_system():
    """
    Остановить real-time систему и очистить ресурсы
    """
    global realtime_manager, websocket_handler
    
    try:
        if realtime_manager:
            # Остановить все активные сессии
            active_sessions = realtime_manager.get_active_sessions()
            for session_id in active_sessions:
                await realtime_manager.stop_session(session_id)
            
            logger.info("All real-time sessions stopped")
        
        # Очистить глобальные переменные
        realtime_manager = None
        websocket_handler = None
        
        logger.info("Real-time transcription system shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during real-time system shutdown: {e}") 
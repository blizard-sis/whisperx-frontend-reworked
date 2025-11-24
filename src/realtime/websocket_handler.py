"""
WebSocket обработчик для real-time транскрипции

Управляет WebSocket соединениями и обрабатывает события real-time транскрипции.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Set
from datetime import datetime
import base64

from fastapi import WebSocket, WebSocketDisconnect
from .models import (
    RealtimeEventType, SessionConfig, AudioChunkEvent,
    create_session_id, create_transcription_partial, create_transcription_final,
    create_error_event
)
from .manager import RealtimeTranscriptionManager

logger = logging.getLogger(__name__)


class RealtimeWebSocketHandler:
    """
    Обработчик WebSocket соединений для real-time транскрипции
    """
    
    def __init__(self, transcription_manager: Optional[RealtimeTranscriptionManager] = None):
        """
        Инициализация обработчика
        
        Args:
            transcription_manager: Менеджер транскрипции или None для создания нового
        """
        self.transcription_manager = transcription_manager or RealtimeTranscriptionManager()
        self.active_connections: Dict[str, WebSocket] = {}  # session_id -> websocket
        self.connection_sessions: Dict[WebSocket, str] = {}  # websocket -> session_id
        
        logger.info("RealtimeWebSocketHandler initialized")
    
    async def handle_connection(self, websocket: WebSocket):
        """
        Обработать новое WebSocket соединение
        
        Args:
            websocket: WebSocket соединение
        """
        await websocket.accept()
        session_id = None
        
        try:
            logger.info(f"New WebSocket connection established: {websocket.client}")
            
            # Отправить приветственное сообщение
            await self._send_status_message(websocket, "connected", "WebSocket connection established")
            
            # Основной цикл обработки сообщений
            async for message in websocket.iter_text():
                try:
                    # Парсинг JSON сообщения
                    data = json.loads(message)
                    event_type = data.get("type")
                    
                    if event_type == RealtimeEventType.SESSION_START:
                        session_id = await self._handle_session_start(websocket, data)
                    
                    elif event_type == RealtimeEventType.SESSION_STOP:
                        await self._handle_session_stop(websocket, data)
                        session_id = None
                    
                    elif event_type == RealtimeEventType.AUDIO_CHUNK:
                        await self._handle_audio_chunk(websocket, data)
                    
                    elif event_type == "ping":
                        await self._send_pong(websocket)
                    
                    else:
                        logger.warning(f"Unknown event type: {event_type}")
                        await self._send_error(websocket, "UNKNOWN_EVENT", f"Unknown event type: {event_type}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    await self._send_error(websocket, "INVALID_JSON", "Invalid JSON format")
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._send_error(websocket, "PROCESSING_ERROR", str(e))
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {websocket.client}")
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        
        finally:
            # Очистка при закрытии соединения
            await self._cleanup_connection(websocket, session_id)
    
    async def _handle_session_start(self, websocket: WebSocket, data: dict) -> str:
        """
        Обработать начало сессии
        
        Args:
            websocket: WebSocket соединение
            data: Данные события
            
        Returns:
            str: ID созданной сессии
        """
        try:
            # Парсинг конфигурации
            config_data = data.get("config", {})
            config = SessionConfig(**config_data)
            
            # Создать сессию
            session_id = await self.transcription_manager.start_session(config)
            
            # Сохранить связь соединение -> сессия
            self.active_connections[session_id] = websocket
            self.connection_sessions[websocket] = session_id
            
            # Отправить подтверждение
            response = {
                "type": "session.started",
                "session_id": session_id,
                "config": config.dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))
            
            logger.info(f"Session started: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            await self._send_error(websocket, "SESSION_START_ERROR", str(e))
            raise
    
    async def _handle_session_stop(self, websocket: WebSocket, data: dict):
        """
        Обработать остановку сессии
        
        Args:
            websocket: WebSocket соединение
            data: Данные события
        """
        try:
            session_id = self.connection_sessions.get(websocket)
            if not session_id:
                await self._send_error(websocket, "NO_ACTIVE_SESSION", "No active session found")
                return
            
            # Остановить сессию
            success = await self.transcription_manager.stop_session(session_id)
            
            if success:
                # Отправить подтверждение
                response = {
                    "type": "session.stopped",
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(response))
                
                # Очистить связи
                del self.active_connections[session_id]
                del self.connection_sessions[websocket]
                
                logger.info(f"Session stopped: {session_id}")
            else:
                await self._send_error(websocket, "SESSION_STOP_ERROR", "Failed to stop session")
                
        except Exception as e:
            logger.error(f"Error stopping session: {e}")
            await self._send_error(websocket, "SESSION_STOP_ERROR", str(e))
    
    async def _handle_audio_chunk(self, websocket: WebSocket, data: dict):
        """
        Обработать аудио чанк
        
        Args:
            websocket: WebSocket соединение
            data: Данные аудио чанка
        """
        try:
            session_id = self.connection_sessions.get(websocket)
            if not session_id:
                await self._send_error(websocket, "NO_ACTIVE_SESSION", "No active session found")
                return
            
            # Извлечь данные
            audio_data_b64 = data.get("audio_data")
            sequence = data.get("sequence", 0)
            
            if not audio_data_b64:
                await self._send_error(websocket, "MISSING_AUDIO_DATA", "Audio data is required")
                return
            
            # Декодировать base64
            try:
                audio_bytes = base64.b64decode(audio_data_b64)
            except Exception as e:
                await self._send_error(websocket, "INVALID_AUDIO_DATA", f"Failed to decode audio data: {e}")
                return
            
            # Обработать чанк
            result = await self.transcription_manager.process_audio_chunk(
                session_id, audio_bytes, sequence
            )
            
            # Отправить результат если есть
            if result:
                # Получить информацию о минутных циклах
                processor = self.transcription_manager.processors.get(session_id)
                window_info = None
                is_final = False
                full_text = result
                
                if processor:
                    stats = processor.get_stats()
                    window_info = stats.get("segment_cycles")
                    
                    # Получить полный накопленный текст (все сегменты)
                    full_text = processor.get_full_accumulated_text()
                    
                    # Отладочная информация
                    logger.debug(f"Stats keys: {list(stats.keys())}")
                    logger.debug(f"Window info: {window_info}")
                    logger.debug(f"Full text length: {len(full_text)}")
                    
                    # Все результаты теперь частичные - не делаем финальных
                    is_final = False
                
                response = {
                    "type": "transcription.final" if is_final else "transcription.partial",
                    "session_id": session_id,
                    "result": {
                        "text": full_text,  # Отправляем полный накопленный текст
                        "confidence": 0.85,  # ЗАГЛУШКА: В реальной реализации получать от модели
                        "is_final": is_final,
                        "window_info": window_info
                    },
                    "sequence": sequence,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(response))
            
            # Периодически отправлять частичные результаты
            if sequence % 10 == 0:  # Каждые 10 чанков
                partial_result = await self.transcription_manager.get_partial_result(session_id)
                if partial_result:
                    response = {
                        "type": "transcription.update",
                        "session_id": session_id,
                        "result": {
                            "text": partial_result,
                            "confidence": 0.80,
                            "is_final": False
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                    
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            await self._send_error(websocket, "AUDIO_PROCESSING_ERROR", str(e))
    
    async def _send_status_message(self, websocket: WebSocket, status: str, message: str):
        """
        Отправить статусное сообщение
        
        Args:
            websocket: WebSocket соединение
            status: Статус
            message: Сообщение
        """
        try:
            response = {
                "type": "status",
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))
        except Exception as e:
            logger.error(f"Error sending status message: {e}")
    
    async def _send_error(self, websocket: WebSocket, error_code: str, error_message: str):
        """
        Отправить сообщение об ошибке
        
        Args:
            websocket: WebSocket соединение
            error_code: Код ошибки
            error_message: Сообщение об ошибке
        """
        try:
            response = {
                "type": "error",
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
    
    async def _send_pong(self, websocket: WebSocket):
        """
        Отправить pong ответ
        
        Args:
            websocket: WebSocket соединение
        """
        try:
            response = {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))
        except Exception as e:
            logger.error(f"Error sending pong: {e}")
    
    async def _cleanup_connection(self, websocket: WebSocket, session_id: Optional[str]):
        """
        Очистить ресурсы при закрытии соединения
        
        Args:
            websocket: WebSocket соединение
            session_id: ID сессии если есть
        """
        try:
            # Остановить сессию если активна
            if session_id and session_id in self.active_connections:
                await self.transcription_manager.stop_session(session_id)
                del self.active_connections[session_id]
            
            # Удалить из маппинга соединений
            if websocket in self.connection_sessions:
                del self.connection_sessions[websocket]
            
            logger.info(f"Connection cleaned up, session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
    
    def get_active_connections_count(self) -> int:
        """
        Получить количество активных соединений
        
        Returns:
            int: Количество активных соединений
        """
        return len(self.active_connections)
    
    def get_connection_stats(self) -> dict:
        """
        Получить статистику соединений
        
        Returns:
            dict: Статистика
        """
        return {
            "active_connections": len(self.active_connections),
            "active_sessions": list(self.active_connections.keys()),
            "total_sessions": len(self.transcription_manager.get_active_sessions())
        } 
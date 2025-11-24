/**
 * Real-Time Audio Manager
 * 
 * Управляет real-time транскрипцией: WebSocket соединение, аудио захват, отправка чанков
 */

class RealtimeAudioManager {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.isRecording = false;
        this.sessionId = null;
        
        // Аудио параметры
        this.audioContext = null;
        this.mediaStream = null;
        this.audioWorkletNode = null;
        this.sampleRate = 24000;
        this.chunkSizeMs = 1000;  // Отправляем каждую секунду
        this.sequenceNumber = 0;
        
        // Конфигурация
        this.config = {
            language: 'ru',
            model: 'large-v3',
            sample_rate: 24000,
            chunk_size_ms: 1000,
            buffer_size_ms: 5000,
            enable_vad: true,
            diarization: false
        };
        
        // Обработчики событий
        this.eventHandlers = {
            onConnected: null,
            onDisconnected: null,
            onSessionStarted: null,
            onSessionStopped: null,
            onTranscriptionPartial: null,
            onTranscriptionFinal: null,
            onError: null,
            onStatus: null
        };
        
        console.log('RealtimeAudioManager initialized');
    }
    
    /**
     * Установить обработчик события
     * @param {string} event - Название события
     * @param {function} handler - Обработчик
     */
    on(event, handler) {
        if (this.eventHandlers.hasOwnProperty(`on${event.charAt(0).toUpperCase() + event.slice(1)}`)) {
            this.eventHandlers[`on${event.charAt(0).toUpperCase() + event.slice(1)}`] = handler;
        }
    }
    
    /**
     * Подключиться к WebSocket серверу
     * @returns {Promise<boolean>} Успешность подключения
     */
    async connect() {
        try {
            if (this.isConnected) {
                console.log('Already connected to WebSocket');
                return true;
            }
            
            // Получить URL WebSocket из конфигурации
            const wsUrl = this._getWebSocketUrl();
            console.log('Connecting to WebSocket:', wsUrl);
            console.log('CONFIG:', window.CONFIG);
            console.log('Current hostname:', window.location.hostname);
            
            this.ws = new WebSocket(wsUrl);
            
            // Настроить обработчики WebSocket
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this._triggerEvent('onConnected');
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.isConnected = false;
                this.sessionId = null;
                this._triggerEvent('onDisconnected', { code: event.code, reason: event.reason });
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this._triggerEvent('onError', { type: 'websocket_error', error: error.message || 'WebSocket connection error' });
            };
            
            this.ws.onmessage = (event) => {
                this._handleWebSocketMessage(event.data);
            };
            
            // Ждем подключения
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('WebSocket connection timeout'));
                }, 5000);
                
                this.ws.onopen = () => {
                    clearTimeout(timeout);
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this._triggerEvent('onConnected');
                    resolve(true);
                };
                
                this.ws.onerror = (error) => {
                    clearTimeout(timeout);
                    console.error('WebSocket connection error:', error);
                    reject(error);
                };
            });
            
        } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            this._triggerEvent('onError', { type: 'connection_error', error: error.message });
            return false;
        }
    }
    
    /**
     * Отключиться от WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.isConnected = false;
            this.sessionId = null;
        }
    }
    
    /**
     * Начать real-time транскрипцию
     * @param {Object} customConfig - Пользовательская конфигурация
     * @returns {Promise<boolean>} Успешность запуска
     */
    async startRealTimeTranscription(customConfig = {}) {
        try {
            if (!this.isConnected) {
                throw new Error('WebSocket not connected');
            }
            
            if (this.isRecording) {
                console.log('Already recording');
                return true;
            }
            
            // Объединить конфигурацию
            const sessionConfig = { ...this.config, ...customConfig };
            
            // Запросить разрешение на микрофон и настроить аудио
            await this._setupAudio();
            
            // Отправить команду начала сессии
            const message = {
                type: 'session.start',
                config: sessionConfig
            };
            
            this._sendWebSocketMessage(message);
            
            // Ждем подтверждения начала сессии
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Session start timeout'));
                }, 10000);
                
                const originalHandler = this.eventHandlers.onSessionStarted;
                this.eventHandlers.onSessionStarted = (data) => {
                    clearTimeout(timeout);
                    this.eventHandlers.onSessionStarted = originalHandler;
                    this.isRecording = true;
                    if (originalHandler) originalHandler(data);
                    resolve(true);
                };
                
                const originalErrorHandler = this.eventHandlers.onError;
                this.eventHandlers.onError = (error) => {
                    clearTimeout(timeout);
                    this.eventHandlers.onError = originalErrorHandler;
                    if (originalErrorHandler) originalErrorHandler(error);
                    reject(new Error(error.error || 'Session start failed'));
                };
            });
            
        } catch (error) {
            console.error('Error starting real-time transcription:', error);
            this._triggerEvent('onError', { type: 'start_error', error: error.message });
            return false;
        }
    }
    
    /**
     * Остановить real-time транскрипцию
     * @returns {Promise<boolean>} Успешность остановки
     */
    async stopRealTimeTranscription() {
        try {
            if (!this.isRecording) {
                console.log('Not recording');
                return true;
            }
            
            // Остановить аудио захват
            await this._cleanupAudio();
            
            // Отправить команду остановки сессии
            if (this.isConnected && this.sessionId) {
                const message = {
                    type: 'session.stop',
                    session_id: this.sessionId
                };
                
                this._sendWebSocketMessage(message);
            }
            
            this.isRecording = false;
            this.sessionId = null;
            this.sequenceNumber = 0;
            
            console.log('Real-time transcription stopped');
            return true;
            
        } catch (error) {
            console.error('Error stopping real-time transcription:', error);
            this._triggerEvent('onError', { type: 'stop_error', error: error.message });
            return false;
        }
    }
    
    /**
     * Получить URL WebSocket из конфигурации
     * @returns {string} WebSocket URL
     */
    _getWebSocketUrl() {
        // Попробовать получить из глобальной конфигурации
        if (typeof window !== 'undefined' && window.CONFIG && window.CONFIG.API) {
            const baseUrl = window.CONFIG.API.BASE_URL || 'http://localhost:8880';
            console.log('Original baseUrl:', baseUrl);
            const wsUrl = baseUrl.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/realtime/ws';
            console.log('Generated WebSocket URL:', wsUrl);
            return wsUrl;
        }
        
        // Определить URL на основе текущего домена
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const host = window.location.hostname;
        
        console.log('Protocol:', protocol, 'Host:', host);
        
        // Для продакшн среды используем API домен без порта
        if (host.includes('localhost')) {
            const wsUrl = `${protocol}://localhost:8880/api/realtime/ws`;
            console.log('Production WebSocket URL:', wsUrl);
            return wsUrl;
        }
        
        // Для разработки используем localhost с портом
        const port = '8880';
        const wsUrl = `${protocol}//${host}:${port}/api/realtime/ws`;
        console.log('Development WebSocket URL:', wsUrl);
        return wsUrl;
    }
    
    /**
     * Отправить сообщение через WebSocket
     * @param {Object} message - Сообщение для отправки
     */
    _sendWebSocketMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            console.log('Sent WebSocket message:', message.type);
        } else {
            console.error('WebSocket not connected, cannot send message');
        }
    }
    
    /**
     * Обработать входящее сообщение WebSocket
     * @param {string} data - JSON данные сообщения
     */
    _handleWebSocketMessage(data) {
        try {
            const message = JSON.parse(data);
            console.log('Received WebSocket message:', message.type);
            
            switch (message.type) {
                case 'status':
                    this._triggerEvent('onStatus', message);
                    break;
                    
                case 'session.started':
                    this.sessionId = message.session_id;
                    this._triggerEvent('onSessionStarted', message);
                    break;
                    
                case 'session.stopped':
                    this.sessionId = null;
                    this.isRecording = false;
                    this._triggerEvent('onSessionStopped', message);
                    break;
                    
                case 'transcription.partial':
                case 'transcription.update':
                    this._triggerEvent('onTranscriptionPartial', message);
                    break;
                    
                case 'transcription.final':
                    this._triggerEvent('onTranscriptionFinal', message);
                    break;
                    
                case 'error':
                    this._triggerEvent('onError', message);
                    break;
                    
                case 'pong':
                    // Ответ на ping, ничего не делаем
                    break;
                    
                default:
                    console.log('Unknown message type:', message.type);
            }
            
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    /**
     * Настроить аудио захват
     * @returns {Promise<void>}
     */
    async _setupAudio() {
        try {
            console.log('Setting up audio...');
            
            // Запросить разрешение на микрофон
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Создать AudioContext
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });
            
            // Загрузить AudioWorklet процессор
            console.log('Загружаем AudioWorklet процессор...');
            await this.audioContext.audioWorklet.addModule('/modules/audio-processor.js');
            console.log('AudioWorklet процессор загружен успешно');
            
            // Создать источник из медиа потока
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            // Создать AudioWorklet узел
            this.audioWorkletNode = new AudioWorkletNode(this.audioContext, 'audio-processor');
            
            // Настроить обработчик сообщений от AudioWorklet
            this.audioWorkletNode.port.onmessage = (event) => {
                if (event.data.type === 'audioData') {
                    this._handleAudioData(event.data.data);
                } else {
                    console.log('Неизвестное сообщение от AudioWorklet:', event.data);
                }
            };
            
            // Подключить источник к процессору
            source.connect(this.audioWorkletNode);
            
            // Настроить размер буфера
            const bufferSize = Math.floor(this.sampleRate * this.chunkSizeMs / 1000);
            this.audioWorkletNode.port.postMessage({
                command: 'updateConfig',
                bufferSize: bufferSize,
                sampleRate: this.sampleRate
            });
            
            console.log('Audio setup completed with real microphone');
            
        } catch (error) {
            console.error('Error setting up audio:', error);
            console.error('Error details:', error.message, error.stack);
            // Fallback к mock обработке если AudioWorklet не поддерживается
            console.log('Falling back to mock audio processing...');
            this._startMockAudioProcessing();
        }
    }
    
    /**
     * Обработать реальные аудио данные от AudioWorklet
     * @param {Int16Array} audioData - Аудио данные
     */
    _handleAudioData(audioData) {
        if (this.isRecording && this.sessionId) {
            // Проверяем, есть ли реальный звук (не тишина)
            const hasSound = Array.from(audioData).some(sample => Math.abs(sample) > 100);
            
            console.log(`Аудио чанк #${this.sequenceNumber}: ${audioData.length} семплов, звук: ${hasSound ? 'ДА' : 'НЕТ'}`);
            
            // Конвертировать в base64
            const audioBase64 = this._arrayBufferToBase64(audioData.buffer);
            
            // Отправить чанк
            const message = {
                type: 'audio.chunk',
                session_id: this.sessionId,
                audio_data: audioBase64,
                sequence: this.sequenceNumber++,
                duration_ms: this.chunkSizeMs
            };
            
            this._sendWebSocketMessage(message);
        }
    }

    /**
     * ЗАГЛУШКА: Имитация обработки аудио
     * Используется как fallback если AudioWorklet не поддерживается
     */
    _startMockAudioProcessing() {
        console.log('Starting mock audio processing...');
        
        // Имитируем отправку аудио чанков каждую секунду
        this.audioProcessingInterval = setInterval(() => {
            if (this.isRecording && this.sessionId) {
                console.log(`Mock аудио чанк #${this.sequenceNumber} (тишина)`);
                
                // Создаем фиктивные аудио данные (тишина)
                const chunkSize = Math.floor(this.sampleRate * this.chunkSizeMs / 1000);
                const audioData = new Int16Array(chunkSize); // Массив нулей (тишина)
                
                // Конвертируем в base64
                const audioBase64 = this._arrayBufferToBase64(audioData.buffer);
                
                // Отправляем чанк
                const message = {
                    type: 'audio.chunk',
                    session_id: this.sessionId,
                    audio_data: audioBase64,
                    sequence: this.sequenceNumber++,
                    duration_ms: this.chunkSizeMs
                };
                
                this._sendWebSocketMessage(message);
            }
        }, this.chunkSizeMs);
    }
    
    /**
     * Очистить аудио ресурсы
     * @returns {Promise<void>}
     */
    async _cleanupAudio() {
        try {
            console.log('Cleaning up audio...');
            
            // Остановить имитацию обработки аудио (fallback)
            if (this.audioProcessingInterval) {
                clearInterval(this.audioProcessingInterval);
                this.audioProcessingInterval = null;
            }
            
            // Отключить AudioWorklet узел
            if (this.audioWorkletNode) {
                this.audioWorkletNode.disconnect();
                this.audioWorkletNode = null;
            }
            
            // Остановить медиа поток
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
                this.mediaStream = null;
            }
            
            // Закрыть AudioContext
            if (this.audioContext) {
                await this.audioContext.close();
                this.audioContext = null;
            }
            
            console.log('Audio cleanup completed');
            
        } catch (error) {
            console.error('Error cleaning up audio:', error);
        }
    }
    
    /**
     * Конвертировать ArrayBuffer в base64
     * @param {ArrayBuffer} buffer - Буфер для конвертации
     * @returns {string} Base64 строка
     */
    _arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
    
    /**
     * Вызвать обработчик события
     * @param {string} eventName - Название события
     * @param {*} data - Данные события
     */
    _triggerEvent(eventName, data = null) {
        const handler = this.eventHandlers[eventName];
        if (handler && typeof handler === 'function') {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in event handler ${eventName}:`, error);
            }
        }
    }
    
    /**
     * Отправить ping для проверки соединения
     */
    ping() {
        if (this.isConnected) {
            this._sendWebSocketMessage({ type: 'ping' });
        }
    }
    
    /**
     * Получить статус менеджера
     * @returns {Object} Статус
     */
    getStatus() {
        return {
            isConnected: this.isConnected,
            isRecording: this.isRecording,
            sessionId: this.sessionId,
            sequenceNumber: this.sequenceNumber,
            config: this.config
        };
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealtimeAudioManager;
} else if (typeof window !== 'undefined') {
    window.RealtimeAudioManager = RealtimeAudioManager;
} 
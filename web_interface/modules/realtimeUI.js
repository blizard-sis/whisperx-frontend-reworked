/**
 * Real-Time UI Manager
 * 
 * Управляет пользовательским интерфейсом для real-time транскрипции
 */

class RealtimeUI {
    constructor() {
        this.isRealtimeMode = false;
        this.isRecording = false;
        this.transcriptionText = '';
        this.sessionId = null;
        
        // DOM элементы (будут инициализированы в init())
        this.realtimeButton = null;
        this.realtimePanel = null;
        this.transcriptionArea = null;
        this.statusIndicator = null;
        this.volumeIndicator = null;
        this.configPanel = null;
        
        // Обработчики событий
        this.eventHandlers = {
            onStartRecording: null,
            onStopRecording: null,
            onConfigChange: null
        };
        
        console.log('RealtimeUI initialized');
    }
    
    /**
     * Инициализировать UI
     */
    init() {
        this._initializeExistingButtons();
        this._createRealtimePanel();
        this._setupEventListeners();
        console.log('RealtimeUI initialized');
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
     * Инициализировать существующие кнопки Real-Time
     */
    _initializeExistingButtons() {
        // Найти существующие кнопки real-time
        this.realtimeButton = document.getElementById('realtime-btn-main') || 
                             document.getElementById('realtime-btn');
        
        if (!this.realtimeButton) {
            console.error('Real-time button not found');
            return;
        }
        
        console.log('Real-time button found and initialized');
    }
    
    /**
     * Создать панель Real-Time
     */
    _createRealtimePanel() {
        // Создать контейнер панели
        this.realtimePanel = document.createElement('div');
        this.realtimePanel.id = 'realtime-panel';
        this.realtimePanel.className = 'realtime-panel hidden';
        
        this.realtimePanel.innerHTML = `
            <div class="realtime-header">
                <h3>
                    <i class="fas fa-broadcast-tower"></i>
                    Real-Time Транскрипция
                </h3>
                <button id="realtime-close" class="btn-close" title="Закрыть">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            
            <div class="realtime-status">
                <div class="status-indicator">
                    <div class="status-dot" id="status-dot"></div>
                    <span id="status-text">Готов к подключению</span>
                </div>
                <div class="cycle-progress">
                    <div class="cycle-info">
                        <span id="window-status">Ожидание...</span>
                        <span id="window-timer">След. обработка: 1с</span>
                    </div>
                    <div id="window-progress-bar" class="progress-bar">
                        <div id="window-progress-fill" class="progress-fill"></div>
                    </div>
                </div>
                <div class="volume-indicator">
                    <div class="volume-bar">
                        <div class="volume-level" id="volume-level"></div>
                    </div>
                </div>
            </div>
            
            <div class="realtime-controls">
                <button id="realtime-start" class="btn btn-start" disabled>
                    <i class="fas fa-play"></i>
                    <span>Начать запись</span>
                </button>
                <button id="realtime-stop" class="btn btn-stop hidden">
                    <i class="fas fa-stop"></i>
                    <span>Остановить</span>
                </button>
                <button id="realtime-config" class="btn btn-config">
                    <i class="fas fa-cog"></i>
                    <span>Настройки</span>
                </button>
            </div>
            
            <div class="realtime-transcription">
                <div class="transcription-header">
                    <h4>Транскрипция:</h4>
                    <div class="transcription-actions">
                        <button id="copy-transcription" class="btn-copy" title="Скопировать">
                            <i class="fas fa-copy"></i>
                        </button>
                        <button id="clear-transcription" class="btn-clear" title="Очистить">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div id="transcription-area" class="transcription-area" placeholder="Текст транскрипции появится здесь..."></div>
            </div>
            
            <div class="realtime-config-panel hidden" id="config-panel">
                <h4>Настройки транскрипции</h4>
                <div class="config-grid">
                    <div class="config-item">
                        <label for="config-language">Язык:</label>
                        <select id="config-language">
                            <option value="ru">Русский</option>
                            <option value="en">English</option>
                            <option value="es">Español</option>
                            <option value="fr">Français</option>
                            <option value="de">Deutsch</option>
                        </select>
                    </div>
                    <div class="config-item">
                        <label for="config-model">Модель:</label>
                        <select id="config-model">
                            <option value="large-v3">Large v3 (лучшее качество)</option>
                            <option value="large-v2">Large v2</option>
                            <option value="medium">Medium (быстрее)</option>
                            <option value="small">Small (очень быстро)</option>
                        </select>
                    </div>
                    <div class="config-item">
                        <label for="config-chunk-size">Размер чанка:</label>
                        <select id="config-chunk-size">
                            <option value="50">50ms (минимальная задержка)</option>
                            <option value="100" selected>100ms (рекомендуется)</option>
                            <option value="200">200ms (стабильнее)</option>
                            <option value="500">500ms (максимальная стабильность)</option>
                        </select>
                    </div>
                    <div class="config-item">
                        <label for="config-vad">
                            <input type="checkbox" id="config-vad" checked>
                            Определение речи (VAD)
                        </label>
                    </div>
                </div>
                <div class="config-actions">
                    <button id="config-save" class="btn btn-primary">Сохранить</button>
                    <button id="config-cancel" class="btn btn-secondary">Отмена</button>
                </div>
            </div>
        `;
        
        // Найти место для вставки панели
        const mainContainer = document.querySelector('.main-container') || 
                            document.querySelector('.container') ||
                            document.body;
        
        mainContainer.appendChild(this.realtimePanel);
        
        // Сохранить ссылки на элементы
        this.transcriptionArea = document.getElementById('transcription-area');
        this.statusIndicator = document.getElementById('status-dot');
        this.volumeIndicator = document.getElementById('volume-level');
        this.configPanel = document.getElementById('config-panel');
        
        console.log('Real-time panel created');
        console.log('transcriptionArea found:', !!this.transcriptionArea);
        console.log('statusIndicator found:', !!this.statusIndicator);
        console.log('volumeIndicator found:', !!this.volumeIndicator);
    }
    
    /**
     * Настроить обработчики событий
     */
    _setupEventListeners() {
        // Кнопка Real-Time
        if (this.realtimeButton) {
            this.realtimeButton.addEventListener('click', () => {
                this.toggleRealtimeMode();
            });
        }
        
        // Кнопки в панели
        const startBtn = document.getElementById('realtime-start');
        const stopBtn = document.getElementById('realtime-stop');
        const configBtn = document.getElementById('realtime-config');
        const closeBtn = document.getElementById('realtime-close');
        const clearBtn = document.getElementById('clear-transcription');
        const copyBtn = document.getElementById('copy-transcription');
        
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                this._triggerEvent('onStartRecording');
            });
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this._triggerEvent('onStopRecording');
            });
        }
        
        if (configBtn) {
            configBtn.addEventListener('click', () => {
                this.toggleConfigPanel();
            });
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hideRealtimeMode();
            });
        }
        
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearTranscription();
            });
        }
        
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                this.copyTranscription();
            });
        }
        
        // Настройки
        const configSaveBtn = document.getElementById('config-save');
        const configCancelBtn = document.getElementById('config-cancel');
        
        if (configSaveBtn) {
            configSaveBtn.addEventListener('click', () => {
                this.saveConfig();
            });
        }
        
        if (configCancelBtn) {
            configCancelBtn.addEventListener('click', () => {
                this.hideConfigPanel();
            });
        }
    }
    
    /**
     * Переключить режим Real-Time
     */
    toggleRealtimeMode() {
        if (this.isRealtimeMode) {
            this.hideRealtimeMode();
        } else {
            this.showRealtimeMode();
        }
    }
    
    /**
     * Показать режим Real-Time
     */
    showRealtimeMode() {
        if (this.realtimePanel) {
            this.realtimePanel.classList.remove('hidden');
            this.isRealtimeMode = true;
            
            // Обновить кнопку
            if (this.realtimeButton) {
                this.realtimeButton.classList.add('active');
                this.realtimeButton.innerHTML = `
                    <i class="fas fa-microphone"></i>
                    <span>Real-Time</span>
                `;
            }
            
            console.log('Real-time mode activated');
        }
    }
    
    /**
     * Скрыть режим Real-Time
     */
    hideRealtimeMode() {
        if (this.realtimePanel) {
            this.realtimePanel.classList.add('hidden');
            this.isRealtimeMode = false;
            
            // Обновить кнопку
            if (this.realtimeButton) {
                this.realtimeButton.classList.remove('active');
                this.realtimeButton.innerHTML = `
                    <i class="fas fa-microphone"></i>
                    <span>Real-Time</span>
                `;
            }
            
            // Остановить запись если активна
            if (this.isRecording) {
                this._triggerEvent('onStopRecording');
            }
            
            console.log('Real-time mode deactivated');
        }
    }
    
    /**
     * Обновить статус подключения
     * @param {string} status - Статус ('connecting', 'connected', 'disconnected', 'error')
     * @param {string} message - Сообщение статуса
     */
    updateConnectionStatus(status, message = '') {
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');
        const startBtn = document.getElementById('realtime-start');
        
        if (statusDot) {
            statusDot.className = `status-dot status-${status}`;
        }
        
        if (statusText) {
            statusText.textContent = message || this._getStatusMessage(status);
        }
        
        // Обновить доступность кнопки старта
        if (startBtn) {
            startBtn.disabled = status !== 'connected';
        }
    }
    
    /**
     * Обновить статус сессии
     * @param {string} status - Статус сессии (recording, stopped, connecting)
     */
    updateSessionStatus(status) {
        this.updateConnectionStatus(status);
        this.updateRecordingStatus(status === 'recording');
    }

    /**
     * Обновить статус записи
     * @param {boolean} recording - Идет ли запись
     */
    updateRecordingStatus(recording) {
        this.isRecording = recording;
        
        const startBtn = document.getElementById('realtime-start');
        const stopBtn = document.getElementById('realtime-stop');
        
        if (startBtn && stopBtn) {
            if (recording) {
                startBtn.classList.add('hidden');
                stopBtn.classList.remove('hidden');
            } else {
                startBtn.classList.remove('hidden');
                stopBtn.classList.add('hidden');
            }
        }
    }
    
    /**
     * Обновить транскрипцию
     * @param {string} text - Текст транскрипции
     * @param {boolean} isFinal - Финальный результат
     * @param {Object} windowInfo - Информация о скользящем окне
     */
    updateTranscription(text, isFinal = false, windowInfo = null) {
        console.log('updateTranscription called:', { text: text?.substring(0, 50), windowInfo });
        
        if (this.transcriptionArea) {
            // Просто показываем весь накопленный текст
            this.transcriptionArea.textContent = text;
            console.log('Транскрипция обновлена, длина:', text?.length || 0);
            
            // Прокрутить вниз
            this.transcriptionArea.scrollTop = this.transcriptionArea.scrollHeight;
        } else {
            console.error('transcriptionArea не найдена!');
        }
        
        // Обновить информацию о прогрессе
        if (windowInfo) {
            this.updateWindowProgress(windowInfo);
        }
    }
    
    /**
     * Обновить прогресс 30-секундных сегментов
     * @param {Object} windowInfo - Информация о 30-секундных сегментах
     */
    updateWindowProgress(windowInfo) {
        const windowStatus = document.getElementById('window-status');
        const windowTimer = document.getElementById('window-timer');
        const progressFill = document.getElementById('window-progress-fill');
        
        if (windowInfo) {
            const currentSegment = windowInfo.current_segment || 1;
            const timeInSegmentMs = windowInfo.time_in_current_segment_ms || 0;
            const nextProcessMs = windowInfo.next_process_in_ms || 0;
            const progressToSegment = windowInfo.progress_to_segment_percent || 0;
            const completedSegmentsCount = windowInfo.completed_segments_count || 0;
            
            // Обновить статус - показать текущий сегмент и время в нем
            if (windowStatus) {
                const timeInSegmentSec = Math.floor(timeInSegmentMs / 1000);
                let statusText = `Сегмент ${currentSegment} (${timeInSegmentSec}с/30с)`;
                
                if (completedSegmentsCount > 0) {
                    statusText += ` | Готово: ${completedSegmentsCount}`;
                }
                
                windowStatus.textContent = statusText;
            }
            
            // Обновить таймер до следующей обработки
            if (windowTimer) {
                const nextSec = Math.ceil(nextProcessMs / 1000);
                
                if (nextSec > 0) {
                    windowTimer.textContent = `След. обработка: ${nextSec}с`;
                } else {
                    windowTimer.textContent = `Обработка...`;
                }
            }
            
            // Обновить прогресс-бар (прогресс к завершению 30-секундного сегмента)
            if (progressFill) {
                progressFill.style.width = `${Math.min(100, progressToSegment)}%`;
            }
        }
    }
    
    /**
     * Очистить транскрипцию
     */
    clearTranscription() {
        this.transcriptionText = '';
        if (this.transcriptionArea) {
            this.transcriptionArea.textContent = '';
        }
    }
    
    /**
     * Скопировать транскрипцию в буфер обмена
     */
    async copyTranscription() {
        try {
            const text = this.transcriptionArea ? this.transcriptionArea.textContent : '';
            
            if (!text || text.trim() === '') {
                this.showError('Нет текста для копирования');
                return;
            }
            
            // Современный API Clipboard
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                this.showSuccessMessage('Текст скопирован в буфер обмена');
            } else {
                // Fallback для старых браузеров
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                try {
                    document.execCommand('copy');
                    this.showSuccessMessage('Текст скопирован в буфер обмена');
                } catch (err) {
                    console.error('Fallback copy failed:', err);
                    this.showError('Не удалось скопировать текст');
                } finally {
                    document.body.removeChild(textArea);
                }
            }
            
            // Визуальная обратная связь - подсветить кнопку
            const copyBtn = document.getElementById('copy-transcription');
            if (copyBtn) {
                copyBtn.classList.add('btn-success');
                setTimeout(() => {
                    copyBtn.classList.remove('btn-success');
                }, 1000);
            }
            
        } catch (error) {
            console.error('Error copying transcription:', error);
            this.showError('Ошибка при копировании текста');
        }
    }
    
    /**
     * Обновить индикатор громкости
     * @param {number} level - Уровень громкости (0-100)
     */
    updateVolumeLevel(level) {
        if (this.volumeIndicator) {
            this.volumeIndicator.style.width = `${Math.min(100, Math.max(0, level))}%`;
        }
    }
    
    /**
     * Показать/скрыть панель настроек
     */
    toggleConfigPanel() {
        if (this.configPanel) {
            this.configPanel.classList.toggle('hidden');
        }
    }
    
    /**
     * Скрыть панель настроек
     */
    hideConfigPanel() {
        if (this.configPanel) {
            this.configPanel.classList.add('hidden');
        }
    }
    
    /**
     * Сохранить конфигурацию
     */
    saveConfig() {
        const config = {
            language: document.getElementById('config-language')?.value || 'ru',
            model: document.getElementById('config-model')?.value || 'large-v3',
            chunk_size_ms: parseInt(document.getElementById('config-chunk-size')?.value) || 100,
            enable_vad: document.getElementById('config-vad')?.checked || true
        };
        
        this._triggerEvent('onConfigChange', config);
        this.hideConfigPanel();
        
        console.log('Config saved:', config);
    }
    
    /**
     * Загрузить конфигурацию в форму
     * @param {Object} config - Конфигурация
     */
    loadConfig(config) {
        const languageSelect = document.getElementById('config-language');
        const modelSelect = document.getElementById('config-model');
        const chunkSizeSelect = document.getElementById('config-chunk-size');
        const vadCheckbox = document.getElementById('config-vad');
        
        if (languageSelect) languageSelect.value = config.language || 'ru';
        if (modelSelect) modelSelect.value = config.model || 'large-v3';
        if (chunkSizeSelect) chunkSizeSelect.value = config.chunk_size_ms || 100;
        if (vadCheckbox) vadCheckbox.checked = config.enable_vad !== false;
    }
    
    /**
     * Показать ошибку
     * @param {string} message - Сообщение об ошибке
     */
    showError(message) {
        // Создать уведомление об ошибке
        const errorDiv = document.createElement('div');
        errorDiv.className = 'realtime-error';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>${message}</span>
            <button class="btn-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Добавить в панель
        if (this.realtimePanel) {
            this.realtimePanel.insertBefore(errorDiv, this.realtimePanel.firstChild);
            
            // Автоматически удалить через 5 секунд
            setTimeout(() => {
                if (errorDiv.parentElement) {
                    errorDiv.remove();
                }
            }, 5000);
        }
    }
    
    /**
     * Показать успешное сообщение
     * @param {string} message - Сообщение об успехе
     */
    showSuccessMessage(message) {
        // Создать уведомление об успехе
        const successDiv = document.createElement('div');
        successDiv.className = 'realtime-success';
        successDiv.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <span>${message}</span>
            <button class="btn-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Добавить в панель
        if (this.realtimePanel) {
            this.realtimePanel.insertBefore(successDiv, this.realtimePanel.firstChild);
            
            // Автоматически удалить через 3 секунды
            setTimeout(() => {
                if (successDiv.parentElement) {
                    successDiv.remove();
                }
            }, 3000);
        }
    }
    
    /**
     * Получить сообщение статуса
     * @param {string} status - Статус
     * @returns {string} Сообщение
     */
    _getStatusMessage(status) {
        const messages = {
            'connecting': 'Подключение...',
            'connected': 'Подключено',
            'disconnected': 'Отключено',
            'recording': 'Запись...',
            'error': 'Ошибка подключения'
        };
        
        return messages[status] || 'Неизвестный статус';
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
     * Получить статус UI
     * @returns {Object} Статус
     */
    getStatus() {
        return {
            isRealtimeMode: this.isRealtimeMode,
            isRecording: this.isRecording,
            transcriptionLength: this.transcriptionText.length,
            sessionId: this.sessionId
        };
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealtimeUI;
} else if (typeof window !== 'undefined') {
    window.RealtimeUI = RealtimeUI;
} 
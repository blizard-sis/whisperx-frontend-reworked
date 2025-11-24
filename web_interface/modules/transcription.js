// Модуль для управления транскрипцией
class TranscriptionManager {
    constructor(apiManager, uiManager) {
        this.apiManager = apiManager;
        this.uiManager = uiManager;
        this.currentTaskId = null;
        this.progressInterval = null;
        this.onTranscriptionComplete = null;
        this.onTranscriptionError = null;
    }

    // Начать транскрипцию
    async startTranscription(file, options = {}) {
        if (!file) {
            this.uiManager.showError(CONFIG.MESSAGES.ERRORS.NO_FILE_SELECTED);
            return;
        }

        // Получить настройки
        const transcriptionOptions = {
            model: options.model || document.getElementById('modelSelect')?.value || CONFIG.TRANSCRIPTION.DEFAULT_MODEL,
            language: options.language || document.getElementById('languageSelect')?.value || CONFIG.TRANSCRIPTION.DEFAULT_LANGUAGE,
            diarize: options.diarize !== undefined ? options.diarize : document.getElementById('diarizeCheck')?.checked || CONFIG.TRANSCRIPTION.DEFAULT_DIARIZE,
            compute_type: options.compute_type || CONFIG.TRANSCRIPTION.DEFAULT_COMPUTE_TYPE,
            batch_size: options.batch_size || CONFIG.TRANSCRIPTION.DEFAULT_BATCH_SIZE
        };

        try {
            // Показать секцию прогресса
            this.showProgressSection(file.name);
            
            // Отправить файл
            const result = await this.apiManager.uploadFile(file, transcriptionOptions);
            this.currentTaskId = result.id;
            
            const taskIdElement = document.getElementById('taskId');
            if (taskIdElement) {
                taskIdElement.textContent = this.currentTaskId;
            }
            
            // Добавить транскрипцию в историю сразу
            if (window.historyManager) {
                window.historyManager.addTranscription({
                    id: this.currentTaskId,
                    filename: file.name,
                    status: 'pending',
                    created_at: new Date().toISOString(),
                    model: transcriptionOptions.model,
                    language: transcriptionOptions.language,
                    progress: 'Задача добавлена в очередь'
                });
            }
            
            // Начать отслеживание прогресса
            this.startProgressTracking();
            
        } catch (error) {
            console.error('Ошибка загрузки файла:', error);
            this.uiManager.showError(`${CONFIG.MESSAGES.ERRORS.FILE_UPLOAD_ERROR}: ${error.message}`);
            this.hideProgressSection();
            
            if (this.onTranscriptionError) {
                this.onTranscriptionError(error);
            }
        }
    }

    // Показать секцию прогресса
    showProgressSection(fileName) {
        const progressSection = document.getElementById('progressSection');
        const uploadSection = document.getElementById('uploadSection');
        const fileNameElement = document.getElementById('fileName');
        
        if (progressSection) {
            progressSection.style.display = 'block';
        }
        if (uploadSection) {
            uploadSection.style.display = 'none';
        }
        if (fileNameElement) {
            fileNameElement.textContent = fileName;
        }
    }

    // Скрыть секцию прогресса
    hideProgressSection() {
        const progressSection = document.getElementById('progressSection');
        const uploadSection = document.getElementById('uploadSection');
        
        if (progressSection) {
            progressSection.style.display = 'none';
        }
        if (uploadSection) {
            uploadSection.style.display = 'block';
        }
    }

    // Начать отслеживание прогресса
    startProgressTracking() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        this.progressInterval = setInterval(async () => {
            try {
                const status = await this.apiManager.getStatus(this.currentTaskId);
                this.updateProgress(status);
                
                if (status.status === 'completed') {
                    this.stopProgressTracking();
                    await this.showResults(status);
                } else if (status.status === 'failed' || status.status === 'error') {
                    this.stopProgressTracking();
                    
                    // Обновляем статус в истории
                    if (window.historyManager) {
                        window.historyManager.updateTranscriptionStatus(this.currentTaskId, {
                            status: status.status,
                            error: status.error || 'Неизвестная ошибка'
                        });
                    }
                    
                    this.uiManager.showError(`Ошибка транскрипции: ${status.error || 'Неизвестная ошибка'}`);
                    this.hideProgressSection();
                }
            } catch (error) {
                console.error('Ошибка получения статуса:', error);
                this.stopProgressTracking();
                
                // Обновляем статус в истории при ошибке сети
                if (window.historyManager && this.currentTaskId) {
                    window.historyManager.updateTranscriptionStatus(this.currentTaskId, {
                        status: 'error',
                        error: `Ошибка получения статуса: ${error.message}`
                    });
                }
                
                this.uiManager.showError(`Ошибка получения статуса: ${error.message}`);
                this.hideProgressSection();
            }
        }, CONFIG.UI.PROGRESS_UPDATE_INTERVAL);
    }

    // Остановить отслеживание прогресса
    stopProgressTracking() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    // Обновить прогресс
    updateProgress(status) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        // Обновляем прогресс-бар
        if (progressFill) {
            let progressPercent = 0;
            
            // Если есть progress_percent в ответе API, используем его
            if (typeof status.progress_percent === 'number') {
                progressPercent = status.progress_percent;
            }
            // Если progress - число, используем его как процент
            else if (typeof status.progress === 'number') {
                progressPercent = status.progress;
            }
            // Если progress - строка, пытаемся извлечь процент
            else if (typeof status.progress === 'string') {
                const match = status.progress.match(/(\d+)%/);
                if (match) {
                    progressPercent = parseInt(match[1]);
                }
            }
            // Для разных статусов устанавливаем примерный прогресс (fallback)
            else {
                switch (status.status) {
                    case 'pending':
                        progressPercent = 5;
                        break;
                    case 'preparing':
                        progressPercent = 10;
                        break;
                    case 'extracting_audio':
                        progressPercent = 15;
                        break;
                    case 'loading_models':
                    case 'loading_whisper_model':
                    case 'loading_align_model':
                    case 'loading_diarize_model':
                        progressPercent = 25;
                        break;
                    case 'loading_audio':
                        progressPercent = 32;
                        break;
                    case 'transcribing':
                        progressPercent = 45;
                        break;
                    case 'aligning':
                        progressPercent = 65;
                        break;
                    case 'diarizing':
                        progressPercent = 72;
                        break;
                    case 'generating_files':
                        progressPercent = 80;
                        break;
                    case 'saving_files':
                        progressPercent = 90;
                        break;
                    case 'cleaning_up':
                        progressPercent = 97;
                        break;
                    case 'completed':
                        progressPercent = 100;
                        break;
                    case 'processing':
                        progressPercent = 50;
                        break;
                }
            }
            
            // Ограничиваем значение от 0 до 100
            progressPercent = Math.max(0, Math.min(100, progressPercent));
            
            progressFill.style.width = `${progressPercent}%`;
        }
        
        // Обновляем текст прогресса
        if (progressText) {
            const displayText = status.progress || this.getStatusDisplayText(status.status);
            const percentText = status.progress_percent ? ` (${status.progress_percent}%)` : '';
            progressText.textContent = displayText + percentText;
        }
        
        // Обновляем статус в истории
        if (window.historyManager && this.currentTaskId) {
            window.historyManager.updateTranscriptionStatus(this.currentTaskId, {
                status: status.status,
                progress: status.progress,
                progress_percent: status.progress_percent
            });
        }
    }
    
    // Получить отображаемый текст для статуса
    getStatusDisplayText(status) {
        const statusTexts = {
            'pending': 'Ожидание обработки',
            'preparing': 'Подготовка к обработке',
            'extracting_audio': 'Извлечение аудио из видео',
            'loading_models': 'Загрузка моделей WhisperX',
            'loading_whisper_model': 'Загрузка модели Whisper',
            'loading_align_model': 'Загрузка модели выравнивания',
            'loading_diarize_model': 'Загрузка модели диаризации',
            'loading_audio': 'Загрузка аудио файла',
            'transcribing': 'Выполнение транскрипции',
            'aligning': 'Выравнивание текста',
            'diarizing': 'Диаризация спикеров',
            'generating_files': 'Генерация файлов субтитров',
            'saving_files': 'Сохранение файлов транскрипции',
            'cleaning_up': 'Очистка временных файлов',
            'completed': 'Транскрипция завершена',
            'processing': 'Обработка',
            'failed': 'Ошибка',
            'error': 'Ошибка'
        };
        
        return statusTexts[status] || status;
    }

    // Показать результаты
    async showResults(status) {
        this.hideProgressSection();
        
        const resultsSection = document.getElementById('resultsSection');
        if (resultsSection) {
            resultsSection.style.display = 'block';
        }
        
        // Вызываем callback если он установлен
        if (this.onTranscriptionComplete) {
            this.onTranscriptionComplete(status);
        }
    }

    // Отменить транскрипцию
    async cancelTranscription() {
        if (!this.currentTaskId) {
            return;
        }
        
        try {
            await this.apiManager.cancelTranscription(this.currentTaskId);
            this.stopProgressTracking();
            this.hideProgressSection();
            this.uiManager.showInfoMessage(CONFIG.MESSAGES.INFO.TRANSCRIPTION_CANCELLED);
            this.currentTaskId = null;
        } catch (error) {
            console.error('Ошибка отмены транскрипции:', error);
            this.uiManager.showError(`Ошибка отмены: ${error.message}`);
        }
    }

    // Получить текущий ID задачи
    getCurrentTaskId() {
        return this.currentTaskId;
    }

    // Установить ID задачи (для загрузки из истории)
    setCurrentTaskId(taskId) {
        this.currentTaskId = taskId;
    }

    // Очистить текущее состояние
    clearCurrentState() {
        this.stopProgressTracking();
        this.currentTaskId = null;
        this.hideProgressSection();
        
        const resultsSection = document.getElementById('resultsSection');
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
    }

    // Установка callback функций
    setOnTranscriptionCompleteCallback(callback) {
        this.onTranscriptionComplete = callback;
    }

    setOnTranscriptionErrorCallback(callback) {
        this.onTranscriptionError = callback;
    }

    // Инициализация обработчиков событий
    initializeEventListeners() {
        const startButton = document.getElementById('startTranscription');
        const cancelButton = document.getElementById('cancelTranscription');
        
        if (startButton) {
            startButton.addEventListener('click', () => {
                // Этот обработчик будет установлен в main.js
            });
        }
        
        if (cancelButton) {
            cancelButton.addEventListener('click', () => this.cancelTranscription());
        }
    }
}

// Экспорт для использования в других модулях
window.TranscriptionManager = TranscriptionManager; 
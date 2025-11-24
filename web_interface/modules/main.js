// Главный модуль приложения
class AppManager {
    constructor() {
        // Инициализация менеджеров
        this.uiManager = new UIManager();
        this.apiManager = new ApiManager();
        this.fileHandler = new FileHandler();
        this.transcriptionManager = new TranscriptionManager(this.apiManager, this.uiManager);
        this.mediaPlayerManager = new MediaPlayerManager(this.apiManager, this.uiManager);
        this.transcriptManager = new TranscriptManager(this.uiManager);
        this.historyManager = new HistoryManager(this.apiManager, this.uiManager);
        this.downloadsManager = new DownloadsManager(this.apiManager, this.uiManager);
        this.summarizationManager = new SummarizationManager(this.apiManager, this.uiManager);
        
        // Real-time модули
        this.realtimeAudioManager = new RealtimeAudioManager();
        this.realtimeUIManager = new RealtimeUI();

        // Глобальные ссылки для обратной совместимости
        window.uiManager = this.uiManager;
        window.apiManager = this.apiManager;
        window.fileHandler = this.fileHandler;
        window.transcriptionManager = this.transcriptionManager;
        window.mediaPlayerManager = this.mediaPlayerManager;
        window.transcriptManager = this.transcriptManager;
        window.historyManager = this.historyManager;
        window.downloadsManager = this.downloadsManager;
        window.summarizationManager = this.summarizationManager;
        window.realtimeAudioManager = this.realtimeAudioManager;
        window.realtimeUIManager = this.realtimeUIManager;

        // Глобальные функции для обратной совместимости
        window.closeModal = () => this.uiManager.closeModal();
    }

    // Инициализация приложения
    async initialize() {
        try {
            // Инициализация всех модулей
            this.initializeModules();
            
            // Настройка взаимодействия между модулями
            this.setupModuleInteractions();
            
            // Загрузка начальных данных
            await this.loadInitialData();
            
            console.log('Приложение успешно инициализировано');
            
        } catch (error) {
            console.error('Ошибка инициализации приложения:', error);
            this.uiManager.showError('Ошибка инициализации приложения');
        }
    }

    // Инициализация всех модулей
    initializeModules() {
        // Инициализация обработчиков событий
        this.fileHandler.initializeEventListeners();
        this.transcriptionManager.initializeEventListeners();
        this.transcriptManager.initializeEventListeners();
        this.downloadsManager.initializeEventListeners();
        this.summarizationManager.initializeEventListeners();
        
        // Инициализация медиаплеера
        this.mediaPlayerManager.initialize();
        
        // Настройка кнопки начала транскрипции
        const startButton = document.getElementById('startTranscription');
        if (startButton) {
            startButton.addEventListener('click', () => this.handleStartTranscription());
        }

        // Настройка кнопки разделения спикеров
        const diarizeToggle = document.getElementById('diarizeToggle');
        if (diarizeToggle) {
            diarizeToggle.addEventListener('click', () => this.handleDiarizeToggle());
            // Инициализация начального состояния
            this.initializeDiarizeButton();
        }

        // Настройка кнопок Real-Time
        const realtimeButtonMain = document.getElementById('realtime-btn-main');
        const realtimeButtonSettings = document.getElementById('realtime-btn');
        
        if (realtimeButtonMain) {
            realtimeButtonMain.addEventListener('click', () => this.handleRealtimeClick());
        }
        
        if (realtimeButtonSettings) {
            realtimeButtonSettings.addEventListener('click', () => this.handleRealtimeClick());
        }
        
        // Инициализация real-time модулей
        this.initializeRealtimeModules();
        
        // Инициализация UI для real-time
        this.realtimeUIManager.init();
    }

    // Настройка взаимодействия между модулями
    setupModuleInteractions() {
        // Callback для выбора файла
        this.fileHandler.setOnFileSelectedCallback((file) => {
            console.log('Файл выбран:', file.name);
        });

        // Callback для завершения транскрипции
        this.transcriptionManager.setOnTranscriptionCompleteCallback(async (status) => {
            await this.handleTranscriptionComplete(status);
        });

        // Callback для ошибки транскрипции
        this.transcriptionManager.setOnTranscriptionErrorCallback((error) => {
            console.error('Ошибка транскрипции:', error);
        });

        // Callback для клика по элементу истории
        this.historyManager.setOnHistoryItemClickCallback(async (taskId, status) => {
            await this.handleHistoryItemClick(taskId, status);
        });

        // Callback для обновления времени медиаплеера
        this.mediaPlayerManager.setOnTimeUpdateCallback((currentTime) => {
            this.transcriptManager.updateTranscriptHighlight(currentTime);
        });
    }

    // Загрузка начальных данных
    async loadInitialData() {
        // Загрузка истории транскрипций
        await this.historyManager.loadTranscriptionHistory();
    }

    // Инициализация real-time модулей
    initializeRealtimeModules() {
        try {
            // Настройка событий real-time аудио менеджера
            this.realtimeAudioManager.on('connected', () => {
                console.log('Real-time: WebSocket подключен');
                this.realtimeUIManager.updateConnectionStatus('connected');
            });
            
            this.realtimeAudioManager.on('disconnected', (data) => {
                console.log('Real-time: WebSocket отключен', data);
                this.realtimeUIManager.updateConnectionStatus('disconnected');
            });
            
            this.realtimeAudioManager.on('sessionStarted', (data) => {
                console.log('Real-time: Сессия начата', data);
                this.realtimeUIManager.updateSessionStatus('recording');
            });
            
            this.realtimeAudioManager.on('sessionStopped', (data) => {
                console.log('Real-time: Сессия остановлена', data);
                this.realtimeUIManager.updateSessionStatus('stopped');
            });
            
            this.realtimeAudioManager.on('transcriptionPartial', (data) => {
                console.log('Real-time: Частичная транскрипция', data);
                console.log('Window info:', data.result?.window_info);
                const windowInfo = data.result?.window_info;
                const text = data.result?.text || data.text;
                console.log('Updating UI with text:', text?.substring(0, 100) + '...');
                this.realtimeUIManager.updateTranscription(text, false, windowInfo);
            });
            
            this.realtimeAudioManager.on('transcriptionFinal', (data) => {
                console.log('Real-time: Финальная транскрипция', data);
                const windowInfo = data.result?.window_info;
                this.realtimeUIManager.updateTranscription(data.result?.text || data.text, true, windowInfo);
            });
            
            this.realtimeAudioManager.on('error', (error) => {
                console.error('Real-time ошибка:', error);
                this.realtimeUIManager.showError(error.error || 'Неизвестная ошибка');
            });
            
            // Настройка событий UI
            this.realtimeUIManager.on('startRecording', async () => {
                await this.startRealtimeRecording();
            });
            
            this.realtimeUIManager.on('stopRecording', async () => {
                await this.stopRealtimeRecording();
            });
            
            this.realtimeUIManager.on('configChange', (config) => {
                console.log('Конфигурация изменена:', config);
                // Обновить конфигурацию в audio manager
                if (this.realtimeAudioManager.config) {
                    Object.assign(this.realtimeAudioManager.config, config);
                }
            });
            
            console.log('Real-time модули инициализированы');
        } catch (error) {
            console.error('Ошибка инициализации real-time модулей:', error);
        }
    }
    
    // Обработка клика по кнопке Real-Time
    async handleRealtimeClick() {
        try {
            // Запросить разрешение на микрофон, если еще не запрошено
            const hasPermission = await this.requestMicrophonePermission();
            if (!hasPermission) {
                this.uiManager.showError('Необходимо разрешение на использование микрофона для real-time транскрипции');
                return;
            }
            
            // Показать real-time интерфейс
            this.realtimeUIManager.showRealtimeMode();
            
            // Автоматически подключиться к WebSocket
            await this.connectToRealtimeServer();
            
        } catch (error) {
            console.error('Ошибка запуска real-time транскрипции:', error);
            this.uiManager.showError('Ошибка запуска real-time транскрипции: ' + error.message);
        }
    }
    
    // Старт real-time записи
    async startRealtimeRecording() {
        try {
            console.log('Запуск real-time записи...');
            this.realtimeUIManager.updateSessionStatus('connecting');
            
            // Запустить real-time транскрипцию
            const success = await this.realtimeAudioManager.startRealTimeTranscription();
            
            if (success) {
                console.log('Real-time запись началась');
                this.realtimeUIManager.updateSessionStatus('recording');
            } else {
                throw new Error('Не удалось начать запись');
            }
        } catch (error) {
            console.error('Ошибка запуска записи:', error);
            this.realtimeUIManager.updateSessionStatus('error');
            this.realtimeUIManager.showError('Ошибка запуска записи: ' + error.message);
        }
    }
    
    // Остановка real-time записи
    async stopRealtimeRecording() {
        try {
            console.log('Остановка real-time записи...');
            
            // Остановить real-time транскрипцию
            const success = await this.realtimeAudioManager.stopRealTimeTranscription();
            
            if (success) {
                console.log('Real-time запись остановлена');
                this.realtimeUIManager.updateSessionStatus('connected');
            } else {
                throw new Error('Не удалось остановить запись');
            }
        } catch (error) {
            console.error('Ошибка остановки записи:', error);
            this.realtimeUIManager.showError('Ошибка остановки записи: ' + error.message);
        }
    }

    // Подключение к real-time серверу
    async connectToRealtimeServer() {
        try {
            console.log('Подключение к real-time серверу...');
            this.realtimeUIManager.updateConnectionStatus('connecting', 'Подключение к серверу...');
            
            // Подключиться к WebSocket
            const connected = await this.realtimeAudioManager.connect();
            
            if (connected) {
                console.log('Подключение к real-time серверу успешно');
                this.realtimeUIManager.updateConnectionStatus('connected', 'Подключено');
            } else {
                throw new Error('Не удалось подключиться к серверу');
            }
        } catch (error) {
            console.error('Ошибка подключения к real-time серверу:', error);
            this.realtimeUIManager.updateConnectionStatus('error', 'Ошибка подключения');
            this.realtimeUIManager.showError('Не удалось подключиться к серверу: ' + error.message);
        }
    }

    // Запрос разрешения на микрофон
    async requestMicrophonePermission() {
        try {
            // Проверяем, есть ли уже разрешение
            const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
            
            if (permissionStatus.state === 'granted') {
                return true;
            }
            
            // Запрашиваем разрешение через getUserMedia
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Останавливаем поток, так как он нужен был только для запроса разрешения
            stream.getTracks().forEach(track => track.stop());
            
            return true;
        } catch (error) {
            console.error('Ошибка запроса разрешения на микрофон:', error);
            return false;
        }
    }

    // Инициализация начального состояния кнопки разделения спикеров
    initializeDiarizeButton() {
        const diarizeToggle = document.getElementById('diarizeToggle');
        const diarizeCheck = document.getElementById('diarizeCheck');
        const diarizeIcon = document.getElementById('diarizeIcon');
        const diarizeText = document.getElementById('diarizeText');
        
        if (!diarizeToggle || !diarizeCheck || !diarizeIcon || !diarizeText) {
            return;
        }
        
        // Устанавливаем начальное состояние из конфигурации
        diarizeCheck.checked = CONFIG.TRANSCRIPTION.DEFAULT_DIARIZE;
        
        // Обновляем внешний вид кнопки
        this.updateDiarizeButtonAppearance();
    }

    // Обработка переключения кнопки разделения спикеров
    handleDiarizeToggle() {
        const diarizeCheck = document.getElementById('diarizeCheck');
        
        if (!diarizeCheck) {
            return;
        }
        
        // Переключаем состояние
        diarizeCheck.checked = !diarizeCheck.checked;
        
        // Обновляем внешний вид кнопки
        this.updateDiarizeButtonAppearance();
    }

    // Обновление внешнего вида кнопки разделения спикеров
    updateDiarizeButtonAppearance() {
        const diarizeToggle = document.getElementById('diarizeToggle');
        const diarizeCheck = document.getElementById('diarizeCheck');
        const diarizeIcon = document.getElementById('diarizeIcon');
        const diarizeText = document.getElementById('diarizeText');
        
        if (!diarizeToggle || !diarizeCheck || !diarizeIcon || !diarizeText) {
            return;
        }
        
        // Обновляем внешний вид кнопки
        if (diarizeCheck.checked) {
            diarizeToggle.classList.add('active');
            diarizeIcon.className = 'fas fa-toggle-on';
            diarizeText.textContent = 'ВКЛ';
        } else {
            diarizeToggle.classList.remove('active');
            diarizeIcon.className = 'fas fa-toggle-off';
            diarizeText.textContent = 'ВЫКЛ';
        }
    }

    // Обработка начала транскрипции
    async handleStartTranscription() {
        const file = this.fileHandler.getSelectedFile();
        
        if (!file) {
            this.uiManager.showError(CONFIG.MESSAGES.ERRORS.NO_FILE_SELECTED);
            return;
        }

        // Проверка типа файла
        if (!this.fileHandler.isValidFileType(file)) {
            this.uiManager.showError('Неподдерживаемый тип файла');
            return;
        }

        // Очистить предыдущие результаты
        this.clearCurrentState();

        // Начать транскрипцию
        await this.transcriptionManager.startTranscription(file);
    }

    // Обработка завершения транскрипции
    async handleTranscriptionComplete(status) {
        const taskId = this.transcriptionManager.getCurrentTaskId();
        
        if (!taskId) {
            console.error('Нет ID задачи для завершенной транскрипции');
            return;
        }

        try {
            console.log('Обработка завершенной транскрипции:', status);
            
            // Установить ID задачи для загрузок (если еще не установлен)
            if (!this.downloadsManager.currentTaskId) {
                this.downloadsManager.setCurrentTaskId(taskId);
            }
            
            // Установить ID задачи для суммаризации
            this.summarizationManager.setCurrentTaskId(taskId);
            
            // Загрузить и отобразить S3 ссылки только если они еще не загружены
            if (!this.downloadsManager.currentS3Links) {
                await this.downloadsManager.loadAndDisplayS3Links(taskId);
            }
            
            // Автоматически отобразить суммаризацию если она уже есть
            if (status.summary && typeof status.summary === 'object') {
                console.log('✅ Найдена существующая суммаризация, сохраняем в менеджер');
                this.summarizationManager.currentSummary = status.summary;
                this.summarizationManager.updateSummarizationStatus('Суммаризация готова', 'success');
            }
            
            // Показать секцию суммаризации (она отобразит сохраненную или загрузит новую)
            this.summarizationManager.showSummarizationSection();
            
            // Отобразить транскрипт если он есть
            if (status.segments && Array.isArray(status.segments)) {
                this.transcriptManager.displayTranscript(status.segments);
            }
            
            // Настроить медиаплеер если есть медиафайлы
            // Проверяем разные возможные источники медиафайлов
            let mediaUrl = null;
            let isVideo = false;
            
            if (status.audio_url) {
                mediaUrl = status.audio_url;
                console.log('Найден audio_url:', mediaUrl);
            } else if (status.video_url) {
                mediaUrl = status.video_url;
                isVideo = true;
                console.log('Найден video_url:', mediaUrl);
            } else if (status.s3_links && status.s3_links.original) {
                mediaUrl = status.s3_links.original;
                // Определяем тип файла по расширению
                const filename = status.filename || '';
                const extension = filename.split('.').pop().toLowerCase();
                isVideo = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', '3gp', 'mts'].includes(extension);
                console.log('Найден s3_links.original:', mediaUrl, 'isVideo:', isVideo, 'extension:', extension);
            }
            
            if (mediaUrl) {
                try {
                    // Создаем объект статуса с правильными полями для медиаплеера
                    const mediaStatus = {
                        ...status,
                        audio_url: isVideo ? null : mediaUrl,
                        video_url: isVideo ? mediaUrl : null
                    };
                    console.log('Настройка медиаплеера с:', mediaStatus);
                    await this.mediaPlayerManager.setupMediaPlayerWithProgress(mediaStatus);
                } catch (mediaError) {
                    console.error('Ошибка настройки медиаплеера:', mediaError);
                    this.uiManager.showInfoMessage('Медиафайл недоступен, но транскрипт готов для просмотра');
                }
            } else {
                console.log('Медиафайл не найден в статусе:', status);
                this.uiManager.showInfoMessage('Медиафайл недоступен, но транскрипт готов для просмотра');
            }
            
            // Обновить статус в истории (транскрипция уже добавлена при старте)
            this.historyManager.updateTranscriptionStatus(taskId, {
                status: 'completed',
                completed_at: new Date().toISOString(),
                filename: status.filename || this.fileHandler.getSelectedFile()?.name || 'Неизвестный файл'
            });
            
            // Показать сообщение об успехе
            this.uiManager.showSuccessMessage('Транскрипция успешно завершена!');
            
        } catch (error) {
            console.error('Ошибка обработки завершенной транскрипции:', error);
            this.uiManager.showError('Ошибка при обработке результатов транскрипции');
        }
    }

    // Обработка клика по элементу истории
    async handleHistoryItemClick(taskId, status) {
        if (status !== 'completed') {
            this.uiManager.showError('Транскрипция не завершена');
            return;
        }

        try {
            // Показать загрузку
            this.historyManager.showHistoryItemLoading(taskId);
            
            // Очистить текущее состояние
            this.clearCurrentState();
            
            // Установить текущий ID задачи сразу
            this.transcriptionManager.setCurrentTaskId(taskId);
            this.downloadsManager.setCurrentTaskId(taskId);
            this.summarizationManager.setCurrentTaskId(taskId);
            
            // Показать секцию результатов
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) {
                resultsSection.style.display = 'block';
            }
            
            // Параллельно загружаем статус транскрипции и S3 ссылки
            const [transcriptionStatus, s3LinksData] = await Promise.allSettled([
                this.apiManager.getStatus(taskId),
                this.apiManager.getS3Links(taskId)
            ]);
            
            // Проверяем статус транскрипции
            if (transcriptionStatus.status === 'rejected' || transcriptionStatus.value.status !== 'completed') {
                throw new Error('Транскрипция не завершена');
            }
            
            // Обрабатываем S3 ссылки (если доступны)
            let s3Links = null;
            if (s3LinksData.status === 'fulfilled') {
                s3Links = s3LinksData.value;
                
                // Сохраняем S3 ссылки в downloads manager
                this.downloadsManager.currentS3Links = s3Links;
                
                // Отображаем S3 ссылки в интерфейсе
                this.downloadsManager.displayS3Links(s3Links);
            }
            
            // Загружаем и отображаем данные транскрипции
            await this.handleTranscriptionComplete(transcriptionStatus.value);
            
            // Скрыть загрузку
            this.historyManager.hideHistoryItemLoading(taskId);
            
        } catch (error) {
            console.error('Ошибка загрузки транскрипции из истории:', error);
            this.historyManager.hideHistoryItemLoading(taskId);
            this.uiManager.showError(`${CONFIG.MESSAGES.ERRORS.LOAD_TRANSCRIPTION_ERROR}: ${error.message}`);
        }
    }

    // Очистка текущего состояния
    clearCurrentState() {
        this.transcriptionManager.clearCurrentState();
        this.mediaPlayerManager.clearMedia();
        this.transcriptManager.clearTranscript();
        this.downloadsManager.clearCurrentState();
        this.summarizationManager.clearCurrentState();
        this.fileHandler.clearSelectedFile();
        this.uiManager.resetInterface();
    }

    // Получение статистики приложения
    getAppStats() {
        return {
            totalTranscriptions: this.historyManager.transcriptions.length,
            currentTranscript: this.transcriptManager.getCurrentTranscript(),
            transcriptStats: this.transcriptManager.getTranscriptStats(),
            isSessionValid: true
        };
    }

    // Экспорт данных приложения
    exportAppData() {
        return {
            config: CONFIG,
            history: this.historyManager.transcriptions,
            currentTranscript: this.transcriptManager.getCurrentTranscript(),
            stats: this.getAppStats()
        };
    }
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    // Создать экземпляр приложения
    window.app = new AppManager();
    
    // Инициализировать приложение
    await window.app.initialize();
});

// Экспорт для использования в других модулях
window.AppManager = AppManager; 
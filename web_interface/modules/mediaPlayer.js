// Модуль для работы с медиаплеером
class MediaPlayerManager {
    constructor(apiManager, uiManager) {
        this.apiManager = apiManager;
        this.uiManager = uiManager;
        this.audioPlayer = null;
        this.videoPlayer = null;
        this.currentTranscript = null;
        this.onTimeUpdate = null;
    }

    // Инициализация медиаплееров
    initialize() {
        this.audioPlayer = document.getElementById('audioPlayer');
        this.videoPlayer = document.getElementById('videoPlayer');
        
        if (this.audioPlayer) {
            this.audioPlayer.addEventListener('timeupdate', () => this.handleTimeUpdate());
        }
        
        if (this.videoPlayer) {
            this.videoPlayer.addEventListener('timeupdate', () => this.handleTimeUpdate());
        }
    }

    // Настройка медиаплеера с прогрессом
    async setupMediaPlayerWithProgress(status) {
        console.log('setupMediaPlayerWithProgress вызван с:', status);
        
        if (!status.audio_url && !status.video_url) {
            console.log('Нет audio_url или video_url в статусе');
            this.uiManager.showInfoMessage(CONFIG.MESSAGES.INFO.MEDIA_LOAD_ERROR);
            return;
        }

        // Показать секцию загрузки медиа
        this.showMediaLoadingSection();

        try {
            const mediaType = status.video_url ? 'video' : 'audio';
            const mediaUrl = status.video_url || status.audio_url;
            
            console.log('Загрузка медиа:', { mediaType, mediaUrl });
            
            if (mediaType === 'video') {
                await this.loadVideoWithProgress(mediaUrl);
            } else {
                await this.loadAudioWithProgress(mediaUrl);
            }
            
            this.hideMediaLoadingSection();
            console.log('Медиа успешно загружено');
            
        } catch (error) {
            console.error('Ошибка загрузки медиа:', error);
            this.hideMediaLoadingSection();
            this.uiManager.showInfoMessage(CONFIG.MESSAGES.INFO.MEDIA_LOAD_ERROR);
        }
    }

    // Загрузка аудио с прогрессом
    async loadAudioWithProgress(audioUrl) {
        console.log('loadAudioWithProgress вызван с URL:', audioUrl);
        
        return new Promise((resolve, reject) => {
            if (!this.audioPlayer) {
                console.error('Audio player не найден');
                reject(new Error('Audio player not found'));
                return;
            }

            // Показать аудиоплеер
            this.audioPlayer.style.display = 'block';
            if (this.videoPlayer) {
                this.videoPlayer.style.display = 'none';
            }

            console.log('Настройка аудиоплеера...');

            // Обновить прогресс загрузки
            this.updateStepStatus('audioStatus', 'loading');
            this.simulateProgress('audioProgress', 'audioProgressText', 3000);

            // Загрузить аудио
            this.audioPlayer.src = audioUrl;
            
            const onCanPlay = () => {
                console.log('Аудио готово к воспроизведению');
                this.updateStepStatus('audioStatus', 'completed');
                this.audioPlayer.removeEventListener('canplay', onCanPlay);
                this.audioPlayer.removeEventListener('error', onError);
                resolve();
            };

            const onError = (error) => {
                console.error('Ошибка загрузки аудио:', error);
                this.updateStepStatus('audioStatus', 'error');
                this.audioPlayer.removeEventListener('canplay', onCanPlay);
                this.audioPlayer.removeEventListener('error', onError);
                reject(error);
            };

            this.audioPlayer.addEventListener('canplay', onCanPlay);
            this.audioPlayer.addEventListener('error', onError);
            
            console.log('Начинаем загрузку аудио...');
            this.audioPlayer.load();
        });
    }

    // Загрузка видео с прогрессом
    async loadVideoWithProgress(videoUrl) {
        console.log('loadVideoWithProgress вызван с URL:', videoUrl);
        
        return new Promise((resolve, reject) => {
            if (!this.videoPlayer) {
                console.error('Video player не найден');
                reject(new Error('Video player not found'));
                return;
            }

            // Показать видеоплеер
            this.videoPlayer.style.display = 'block';
            if (this.audioPlayer) {
                this.audioPlayer.style.display = 'none';
            }

            console.log('Настройка видеоплеера...');

            // Обновить прогресс загрузки
            this.updateStepStatus('videoStatus', 'loading');
            this.simulateProgress('videoProgress', 'videoProgressText', 5000);

            // Загрузить видео
            this.videoPlayer.src = videoUrl;
            
            const onCanPlay = () => {
                console.log('Видео готово к воспроизведению');
                this.updateStepStatus('videoStatus', 'completed');
                this.videoPlayer.removeEventListener('canplay', onCanPlay);
                this.videoPlayer.removeEventListener('error', onError);
                resolve();
            };

            const onError = (error) => {
                console.error('Ошибка загрузки видео:', error);
                this.updateStepStatus('videoStatus', 'error');
                this.videoPlayer.removeEventListener('canplay', onCanPlay);
                this.videoPlayer.removeEventListener('error', onError);
                reject(error);
            };

            this.videoPlayer.addEventListener('canplay', onCanPlay);
            this.videoPlayer.addEventListener('error', onError);
            
            console.log('Начинаем загрузку видео...');
            this.videoPlayer.load();
        });
    }

    // Обработка обновления времени
    handleTimeUpdate() {
        if (this.onTimeUpdate && typeof this.onTimeUpdate === 'function') {
            const currentTime = this.getCurrentTime();
            this.onTimeUpdate(currentTime);
        }
    }

    // Получить текущее время воспроизведения
    getCurrentTime() {
        if (this.audioPlayer && this.audioPlayer.style.display !== 'none') {
            return this.audioPlayer.currentTime;
        } else if (this.videoPlayer && this.videoPlayer.style.display !== 'none') {
            return this.videoPlayer.currentTime;
        }
        return 0;
    }

    // Установить время воспроизведения
    setCurrentTime(time) {
        if (this.audioPlayer && this.audioPlayer.style.display !== 'none') {
            this.audioPlayer.currentTime = time;
        } else if (this.videoPlayer && this.videoPlayer.style.display !== 'none') {
            this.videoPlayer.currentTime = time;
        }
    }

    // Воспроизвести/приостановить
    togglePlayPause() {
        const activePlayer = this.getActivePlayer();
        if (activePlayer) {
            if (activePlayer.paused) {
                activePlayer.play();
            } else {
                activePlayer.pause();
            }
        }
    }

    // Получить активный плеер
    getActivePlayer() {
        if (this.audioPlayer && this.audioPlayer.style.display !== 'none') {
            return this.audioPlayer;
        } else if (this.videoPlayer && this.videoPlayer.style.display !== 'none') {
            return this.videoPlayer;
        }
        return null;
    }

    // Показать секцию загрузки медиа
    showMediaLoadingSection() {
        let mediaLoadingSection = document.getElementById('mediaLoadingSection');
        
        if (!mediaLoadingSection) {
            mediaLoadingSection = this.createMediaLoadingSection();
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) {
                resultsSection.insertBefore(mediaLoadingSection, resultsSection.firstChild);
            }
        }
        
        mediaLoadingSection.style.display = 'block';
        this.startMediaLoadingAnimation();
    }

    // Скрыть секцию загрузки медиа
    hideMediaLoadingSection() {
        const mediaLoadingSection = document.getElementById('mediaLoadingSection');
        if (mediaLoadingSection) {
            mediaLoadingSection.style.display = 'none';
        }
        this.stopMediaLoadingAnimation();
    }

    // Создать секцию загрузки медиа
    createMediaLoadingSection() {
        const section = document.createElement('div');
        section.id = 'mediaLoadingSection';
        section.className = 'media-loading-section';
        section.innerHTML = `
            <div class="media-loading-card">
                <h3><i class="fas fa-download"></i> Загрузка медиафайлов</h3>
                <div class="media-loading-steps">
                    <div class="loading-step">
                        <div class="step-icon">
                            <i class="fas fa-music" id="audioStatus"></i>
                        </div>
                        <div class="step-content">
                            <div class="step-title">Загрузка аудио</div>
                            <div class="step-progress">
                                <div class="progress-bar">
                                    <div class="progress-fill" id="audioProgress"></div>
                                </div>
                                <span class="progress-text" id="audioProgressText">0%</span>
                            </div>
                        </div>
                    </div>
                    <div class="loading-step">
                        <div class="step-icon">
                            <i class="fas fa-video" id="videoStatus"></i>
                        </div>
                        <div class="step-content">
                            <div class="step-title">Загрузка видео</div>
                            <div class="step-progress">
                                <div class="progress-bar">
                                    <div class="progress-fill" id="videoProgress"></div>
                                </div>
                                <span class="progress-text" id="videoProgressText">0%</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="media-loading-actions">
                    <button class="btn btn-outline" onclick="window.mediaPlayerManager?.skipMediaLoading()">
                        <i class="fas fa-forward"></i> Пропустить загрузку медиа
                    </button>
                </div>
                <p class="media-loading-info">
                    <i class="fas fa-info-circle"></i>
                    Загружаем медиафайлы для синхронизации с транскриптом. Это может занять некоторое время.
                </p>
            </div>
        `;
        return section;
    }

    // Пропустить загрузку медиа
    skipMediaLoading() {
        this.hideMediaLoadingSection();
        this.uiManager.showInfoMessage(CONFIG.MESSAGES.INFO.MEDIA_LOADING_SKIPPED);
    }

    // Обновить статус шага
    updateStepStatus(statusId, status) {
        const statusElement = document.getElementById(statusId);
        if (statusElement) {
            statusElement.className = 'fas';
            switch (status) {
                case 'loading':
                    statusElement.classList.add('fa-spinner', 'fa-spin');
                    statusElement.style.color = '#007bff';
                    break;
                case 'completed':
                    statusElement.classList.add('fa-check-circle');
                    statusElement.style.color = '#28a745';
                    break;
                case 'error':
                    statusElement.classList.add('fa-times-circle');
                    statusElement.style.color = '#dc3545';
                    break;
            }
        }
    }

    // Симуляция прогресса
    simulateProgress(progressId, textId, duration) {
        const progressElement = document.getElementById(progressId);
        const textElement = document.getElementById(textId);
        
        if (!progressElement || !textElement) return;
        
        let progress = 0;
        const interval = 100;
        const step = (interval / duration) * 100;
        
        const progressInterval = setInterval(() => {
            progress += step;
            if (progress >= 100) {
                progress = 100;
                clearInterval(progressInterval);
            }
            
            progressElement.style.width = `${progress}%`;
            textElement.textContent = `${Math.round(progress)}%`;
        }, interval);
    }

    // Запуск анимации загрузки медиа
    startMediaLoadingAnimation() {
        // Можно добавить дополнительные анимации
    }

    // Остановка анимации загрузки медиа
    stopMediaLoadingAnimation() {
        // Можно добавить логику остановки анимаций
    }

    // Установка callback для обновления времени
    setOnTimeUpdateCallback(callback) {
        this.onTimeUpdate = callback;
    }

    // Установка текущего транскрипта
    setCurrentTranscript(transcript) {
        this.currentTranscript = transcript;
    }

    // Очистка медиаплееров
    clearMedia() {
        if (this.audioPlayer) {
            this.audioPlayer.src = '';
            this.audioPlayer.style.display = 'none';
        }
        
        if (this.videoPlayer) {
            this.videoPlayer.src = '';
            this.videoPlayer.style.display = 'none';
        }
        
        this.hideMediaLoadingSection();
    }
}

// Экспорт для использования в других модулях
window.MediaPlayerManager = MediaPlayerManager; 
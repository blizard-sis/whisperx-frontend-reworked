// Модуль для работы с загрузками и S3
class DownloadsManager {
    constructor(apiManager, uiManager) {
        this.apiManager = apiManager;
        this.uiManager = uiManager;
        this.currentTaskId = null;
        this.currentS3Links = null;
    }

    // Инициализация обработчиков событий
    initializeEventListeners() {
        // Обработчики событий теперь устанавливаются динамически в updateDownloadButtons
        // в зависимости от наличия S3 ссылок
        console.log('[Downloads] Модуль загрузок инициализирован');
    }

    // Установка текущего ID задачи
    setCurrentTaskId(taskId) {
        this.currentTaskId = taskId;
        this.currentS3Links = null;
    }

    // Загрузка и отображение S3 ссылок
    async loadAndDisplayS3Links(taskId) {
        try {
            const s3LinksData = await this.apiManager.getS3Links(taskId);
            
            // Сохраняем ссылки для использования в кнопках скачивания
            this.currentS3Links = s3LinksData;
            
            // Отображаем S3 ссылки в интерфейсе
            this.displayS3Links(s3LinksData);
            
            console.log('[Downloads] S3 ссылки успешно загружены и отображены');
            
        } catch (error) {
            console.error('[Downloads] Ошибка загрузки S3 ссылок:', error);
            this.currentS3Links = null;
            
            // Не показываем ошибку пользователю, просто скрываем секцию S3
            const downloadsCollapsible = document.getElementById('downloadsCollapsible');
            if (downloadsCollapsible) {
                downloadsCollapsible.style.display = 'none';
            }
            
            // Уведомляем суммаризацию об отсутствии данных
            if (window.summarizationManager) {
                console.log('[Downloads] Уведомляем суммаризацию об ошибке загрузки S3 ссылок');
                window.summarizationManager.updateSummarizationUI();
            }
        }
    }

    // Отображение S3 ссылок
    displayS3Links(s3Links) {
        const downloadsCollapsible = document.getElementById('downloadsCollapsible');
        const s3LinksGrid = document.getElementById('s3LinksGrid');
        const downloadsCount = document.getElementById('downloadsCount');
        
        if (!downloadsCollapsible || !s3LinksGrid) return;

        if (!s3Links || Object.keys(s3Links).length === 0) {
            downloadsCollapsible.style.display = 'none';
            return;
        }

        s3LinksGrid.innerHTML = '';
        downloadsCollapsible.style.display = 'block';

        // Организуем форматы по категориям
        const categories = [
            {
                title: 'Документы',
                icon: 'fa-file-text',
                description: 'Текстовые форматы для редактирования',
                formats: [
                    { keys: ['json', 'full_json_s3_url', 'transcript_json', 'json_url'], displayAs: 'json' },
                    { keys: ['docx', 'docx_url', 'word'], displayAs: 'docx' },
                    { keys: ['pdf', 'pdf_url'], displayAs: 'pdf' }
                ]
            },
            {
                title: 'Субтитры',
                icon: 'fa-closed-captioning',
                description: 'Форматы для видеоплееров',
                formats: [
                    { keys: ['srt', 'srt_url'], displayAs: 'srt' },
                    { keys: ['vtt', 'vtt_url'], displayAs: 'vtt' },
                    { keys: ['tsv', 'tsv_url'], displayAs: 'tsv' }
                ]
            },
            {
                title: 'Медиафайлы',
                icon: 'fa-play-circle',
                description: 'Оригинальные аудио и видео',
                formats: [
                    { keys: ['original', 'audio_url', 'video_url'], displayAs: 'audio' }
                ]
            }
        ];

        let totalFiles = 0;

        categories.forEach(category => {
            const availableFormats = [];
            
            // Проверяем какие форматы доступны в этой категории
            category.formats.forEach(({keys, displayAs}) => {
                let url = null;
                for (const key of keys) {
                    if (s3Links[key]) {
                        url = s3Links[key];
                        break;
                    }
                }
                if (url) {
                    availableFormats.push({ displayAs, url });
                    totalFiles++;
                }
            });

            // Создаем секцию категории только если есть доступные форматы
            if (availableFormats.length > 0) {
                const categorySection = this.createCategorySection(category, availableFormats);
                s3LinksGrid.appendChild(categorySection);
            }
        });

        // Обновляем счетчик файлов
        if (downloadsCount) {
            downloadsCount.textContent = `(${totalFiles} ${this.getFileCountText(totalFiles)})`;
        }
        
        // Уведомляем суммаризацию о том, что S3 ссылки загружены
        if (window.summarizationManager) {
            console.log('[Downloads] Уведомляем суммаризацию об обновлении S3 ссылок');
            window.summarizationManager.updateSummarizationUI();
        }
    }

    // Создание секции категории
    createCategorySection(category, formats) {
        const section = document.createElement('div');
        section.className = 'download-category';
        
        section.innerHTML = `
            <div class="category-header">
                <div class="category-icon">
                    <i class="fas ${category.icon}"></i>
                </div>
                <div class="category-info">
                    <h4 class="category-title">${category.title}</h4>
                    <p class="category-description">${category.description}</p>
                </div>
            </div>
            <div class="category-items">
                ${formats.map(format => this.createCategoryItem(format.displayAs, format.url)).join('')}
            </div>
        `;
        
        return section;
    }

    // Создание элемента в категории
    createCategoryItem(format, url) {
        const formatInfo = this.getFormatInfo(format);
        
        return `
            <div class="category-item">
                <div class="item-info">
                    <div class="item-icon">
                        <i class="fas ${formatInfo.icon}"></i>
                    </div>
                    <div class="item-details">
                        <span class="item-name">${formatInfo.label}</span>
                        <span class="item-description">${formatInfo.description}</span>
                    </div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-primary btn-compact" onclick="window.downloadsManager?.downloadS3File('${url}')">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn btn-outline btn-compact" onclick="window.downloadsManager?.copyS3Link('${url}', this)">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
            </div>
        `;
    }

    // Получение информации о формате
    getFormatInfo(format) {
        const formatMap = {
            json: {
                label: 'JSON',
                description: 'Полные данные транскрипции',
                icon: 'fa-code'
            },
            srt: {
                label: 'SRT',
                description: 'Субтитры для видео',
                icon: 'fa-closed-captioning'
            },
            vtt: {
                label: 'VTT',
                description: 'Web субтитры',
                icon: 'fa-closed-captioning'
            },
            tsv: {
                label: 'TSV',
                description: 'Табличные данные',
                icon: 'fa-table'
            },
            docx: {
                label: 'DOCX',
                description: 'Документ Word',
                icon: 'fa-file-word'
            },
            pdf: {
                label: 'PDF',
                description: 'PDF документ',
                icon: 'fa-file-pdf'
            },
            audio: {
                label: 'Аудио',
                description: 'Аудиофайл',
                icon: 'fa-music'
            },
            video: {
                label: 'Видео',
                description: 'Видеофайл',
                icon: 'fa-video'
            }
        };

        return formatMap[format] || {
            label: format.toUpperCase(),
            description: 'Файл',
            icon: 'fa-file'
        };
    }

    // Скачивание файла напрямую из S3
    downloadS3File(url) {
        // Создаем временную ссылку для скачивания
        const a = document.createElement('a');
        a.href = url;
        a.download = ''; // Браузер определит имя файла из URL
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    // Открытие S3 ссылки (теперь тоже скачивает)
    openS3Link(url) {
        this.downloadS3File(url);
    }

    // Копирование S3 ссылки
    async copyS3Link(url, button) {
        try {
            await navigator.clipboard.writeText(url);
            
            // Временно изменить текст кнопки
            const originalHTML = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i> Скопировано';
            button.classList.add('btn-success');
            button.classList.remove('btn-outline');
            
            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline');
            }, 2000);
            
        } catch (error) {
            console.error('Ошибка копирования:', error);
            this.uiManager.showError('Не удалось скопировать ссылку');
        }
    }

    // Скачивание файла
    async downloadFile(format) {
        if (!this.currentTaskId) {
            this.uiManager.showError('Нет активной транскрипции для скачивания');
            return;
        }

        console.log(`[Downloads] Скачиваем файл через API, формат: ${format}`);

        // Скачивание через API (используется когда нет S3 ссылок)
        const button = document.getElementById(`download${format.charAt(0).toUpperCase() + format.slice(1)}`);
        
        try {
            // Показать состояние загрузки
            if (button) {
                const originalHTML = button.innerHTML;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';
                button.disabled = true;
            }

            console.log(`[Downloads] Делаем запрос к API для формата: ${format}`);
            const response = await this.apiManager.downloadFile(this.currentTaskId, format);
            
            // Получить имя файла из заголовков или создать по умолчанию
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `transcription_${this.currentTaskId}.${format}`;
            
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            // Скачать файл
            const blob = await response.blob();
            this.downloadBlob(blob, filename);
            
            // Показать сообщение об успехе
            this.uiManager.showSuccessMessage(CONFIG.MESSAGES.SUCCESS.FILE_DOWNLOADED);
            
        } catch (error) {
            console.error('Ошибка скачивания файла:', error);
            this.uiManager.showError(`${CONFIG.MESSAGES.ERRORS.DOWNLOAD_ERROR}: ${error.message}`);
        } finally {
            // Восстановить кнопку
            if (button) {
                const formatInfo = CONFIG.EXPORT.FORMATS[format];
                button.innerHTML = `<i class="${formatInfo.icon}"></i> ${formatInfo.label}`;
                button.disabled = false;
            }
        }
    }

    // Скачивание blob как файла
    downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        
        document.body.appendChild(a);
        a.click();
        
        // Очистка
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    // Скачивание файла с прогрессом
    async downloadFileWithProgress(format, onProgress) {
        if (!this.currentTaskId) {
            this.uiManager.showError('Нет активной транскрипции для скачивания');
            return;
        }

        try {
            const response = await this.apiManager.downloadFile(this.currentTaskId, format);
            
            if (!response.body) {
                throw new Error('ReadableStream не поддерживается');
            }

            const contentLength = response.headers.get('content-length');
            const total = parseInt(contentLength, 10);
            let loaded = 0;

            const reader = response.body.getReader();
            const chunks = [];

            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                chunks.push(value);
                loaded += value.length;
                
                if (onProgress && total) {
                    onProgress((loaded / total) * 100);
                }
            }

            // Создать blob из chunks
            const blob = new Blob(chunks);
            const filename = `transcription_${this.currentTaskId}.${format}`;
            this.downloadBlob(blob, filename);
            
            return blob;
            
        } catch (error) {
            console.error('Ошибка скачивания с прогрессом:', error);
            // Fallback к обычному скачиванию
            return this.downloadFile(format);
        }
    }

    // Получение размера файла
    async getFileSize(format) {
        if (!this.currentTaskId) return null;

        try {
            const response = await fetch(
                `${this.apiManager.baseUrl}${this.apiManager.config.ENDPOINTS.DOWNLOAD_TRANSCRIPT}/${this.currentTaskId}/${format}`,
                { method: 'HEAD' }
            );
            
            const contentLength = response.headers.get('content-length');
            return contentLength ? parseInt(contentLength, 10) : null;
            
        } catch (error) {
            console.error('Ошибка получения размера файла:', error);
            return null;
        }
    }

    // Проверка доступности файла для скачивания
    async checkFileAvailability(format) {
        if (!this.currentTaskId) return false;

        try {
            const response = await fetch(
                `${this.apiManager.baseUrl}${this.apiManager.config.ENDPOINTS.DOWNLOAD_TRANSCRIPT}/${this.currentTaskId}/${format}`,
                { method: 'HEAD' }
            );
            
            return response.ok;
            
        } catch (error) {
            console.error('Ошибка проверки доступности файла:', error);
            return false;
        }
    }

    // Массовое скачивание всех форматов
    async downloadAllFormats() {
        if (!this.currentTaskId) {
            this.uiManager.showError('Нет активной транскрипции для скачивания');
            return;
        }

        const formats = Object.keys(CONFIG.EXPORT.FORMATS);
        const downloadPromises = formats.map(format => this.downloadFile(format));
        
        try {
            await Promise.all(downloadPromises);
            this.uiManager.showSuccessMessage('Все файлы успешно скачаны');
        } catch (error) {
            console.error('Ошибка массового скачивания:', error);
            this.uiManager.showError('Ошибка при скачивании некоторых файлов');
        }
    }

    // Очистка текущего состояния
    clearCurrentState() {
        this.currentTaskId = null;
        this.currentS3Links = null;
        
        // Скрыть S3 секцию
        const downloadsCollapsible = document.getElementById('downloadsCollapsible');
        if (downloadsCollapsible) {
            downloadsCollapsible.style.display = 'none';
        }
        
        // Очистить S3 ссылки
        const s3LinksGrid = document.getElementById('s3LinksGrid');
        if (s3LinksGrid) {
            s3LinksGrid.innerHTML = '';
        }
    }

    // Получение текста для счетчика файлов
    getFileCountText(count) {
        if (count === 1) return 'файл';
        if (count >= 2 && count <= 4) return 'файла';
        return 'файлов';
    }

    // Переключение свернутого меню
    toggleDownloadsMenu() {
        const downloadsCollapsible = document.getElementById('downloadsCollapsible');
        const downloadsChevron = document.getElementById('downloadsChevron');
        
        if (!downloadsCollapsible) return;
        
        const isExpanded = downloadsCollapsible.classList.contains('expanded');
        
        if (isExpanded) {
            downloadsCollapsible.classList.remove('expanded');
        } else {
            downloadsCollapsible.classList.add('expanded');
        }
    }
}

// Глобальная функция для переключения меню скачивания
function toggleDownloadsMenu() {
    if (window.downloadsManager && typeof window.downloadsManager.toggleDownloadsMenu === 'function') {
        window.downloadsManager.toggleDownloadsMenu();
    }
}

// Экспорт для использования в других модулях
window.DownloadsManager = DownloadsManager; 
// Модуль для обработки файлов
class FileHandler {
    constructor() {
        this.selectedFile = null;
        this.onFileSelected = null; // callback функция
    }

    // Инициализация обработчиков событий
    initializeEventListeners() {
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const selectFileBtn = document.getElementById('selectFileBtn');
        
        if (fileInput) {
            fileInput.addEventListener('change', (event) => this.handleFileSelect(event));
        }
        
        if (selectFileBtn) {
            selectFileBtn.addEventListener('click', (event) => {
                event.stopPropagation(); // Предотвращаем всплытие события
                fileInput?.click();
            });
        }
        
        if (uploadArea) {
            uploadArea.addEventListener('click', (event) => {
                // Проверяем, что клик был не по кнопке
                if (!event.target.closest('#selectFileBtn') && !event.target.closest('button')) {
                    event.stopPropagation(); // Предотвращаем всплытие события
                    fileInput?.click();
                }
            });
            uploadArea.addEventListener('dragover', (event) => this.handleDragOver(event));
            uploadArea.addEventListener('dragleave', (event) => this.handleDragLeave(event));
            uploadArea.addEventListener('drop', (event) => this.handleFileDrop(event));
        }
    }

    // Обработка выбора файла
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            // Предотвращаем повторную обработку того же файла
            if (this.selectedFile && this.selectedFile.name === file.name && 
                this.selectedFile.size === file.size && 
                this.selectedFile.lastModified === file.lastModified) {
                console.log('Файл уже выбран, пропускаем повторную обработку');
                return;
            }
            this.setSelectedFile(file);
        }
    }

    // Обработка перетаскивания файлов
    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('dragover');
    }

    handleDragLeave(event) {
        event.currentTarget.classList.remove('dragover');
    }

    handleFileDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('dragover');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.files = files;
            }
            this.setSelectedFile(file);
        }
    }

    // Установка выбранного файла
    setSelectedFile(file) {
        this.selectedFile = file;
        this.showFileSelected(file);
        
        // Вызываем callback если он установлен
        if (this.onFileSelected && typeof this.onFileSelected === 'function') {
            this.onFileSelected(file);
        }
    }

    // Показать выбранный файл
    showFileSelected(file) {
        const settingsPanel = document.getElementById('settingsPanel');
        if (settingsPanel) {
            settingsPanel.style.display = 'block';
        }
        
        // Обновить информацию о файле
        const uploadContent = document.querySelector('.upload-content h3');
        if (uploadContent) {
            uploadContent.textContent = `Выбран файл: ${file.name}`;
        }
        
        // Показать размер файла
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);
        const uploadDesc = document.querySelector('.upload-content p');
        if (uploadDesc) {
            uploadDesc.innerHTML = `Размер: ${fileSize} МБ | Тип: ${file.type}<br>
                Поддерживаются: MP3, M4A, WAV, MP4, AVI, MKV и другие<br>
                Экспорт в 6 форматов: JSON, SRT, VTT, TSV, DOCX, PDF<br>
                <strong>💾 Файлы сохраняются локально и доступны через API</strong>`;
        }
    }

    // Получить выбранный файл
    getSelectedFile() {
        return this.selectedFile;
    }

    // Проверка типа файла
    isValidFileType(file) {
        const audioFormats = CONFIG.FILE_FORMATS.AUDIO;
        const videoFormats = CONFIG.FILE_FORMATS.VIDEO;
        const allFormats = [...audioFormats, ...videoFormats];
        
        const fileExtension = file.name.split('.').pop().toLowerCase();
        return allFormats.includes(fileExtension);
    }

    // Получение типа медиа (audio/video)
    getMediaType(file) {
        const audioFormats = CONFIG.FILE_FORMATS.AUDIO;
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        return audioFormats.includes(fileExtension) ? 'audio' : 'video';
    }

    // Очистка выбранного файла
    clearSelectedFile() {
        this.selectedFile = null;
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.value = '';
        }
        
        const settingsPanel = document.getElementById('settingsPanel');
        if (settingsPanel) {
            settingsPanel.style.display = 'none';
        }
        
        // Восстановить исходный текст
        const uploadContent = document.querySelector('.upload-content h3');
        if (uploadContent) {
            uploadContent.textContent = 'Перетащите файл сюда или нажмите для выбора';
        }
        
        const uploadDesc = document.querySelector('.upload-content p');
        if (uploadDesc) {
            uploadDesc.innerHTML = `Поддерживаются: MP3, M4A, WAV, MP4, AVI, MKV и другие<br>
                Экспорт в 6 форматов: JSON, SRT, VTT, TSV, DOCX, PDF<br>
                <strong>💾 Файлы сохраняются локально и доступны через API</strong>`;
        }
    }

    // Установка callback функции для обработки выбора файла
    setOnFileSelectedCallback(callback) {
        this.onFileSelected = callback;
    }
}

// Экспорт для использования в других модулях
window.FileHandler = FileHandler; 
// Конфигурация AI-Transcribe Web Interface
const CONFIG = {
    // API настройки
    API: {
        BASE_URL: 'http://10.11.35.214:8880',
        // HF_TOKEN передается сервером, не храним в клиентском коде
        ENDPOINTS: {
            UPLOAD: '/api/upload',
            STATUS: '/api/status',
            TRANSCRIPTIONS: '/api/transcriptions',
            DOWNLOAD_AUDIO: '/api/download/audio',
            DOWNLOAD_TRANSCRIPT: '/api/download/transcript',
            DOWNLOAD_SUBTITLE: '/api/download/subtitle',
            DELETE_TRANSCRIPTION: '/api/transcription',
            S3_LINKS: '/api/s3-links',  // Эндпоинт для получения ссылок на локальные файлы
            SUMMARIZE: '/api/summarize',  // Эндпоинт для суммаризации
            SUMMARIZATION_CONFIG: '/api/config/summarization'  // Эндпоинт для конфигурации суммаризации
        }
    },

    // Настройки интерфейса
    UI: {
        PROGRESS_UPDATE_INTERVAL: 2000, // Интервал обновления прогресса в мс
        NOTIFICATION_DURATION: 3000, // Длительность показа уведомлений в мс
        INFO_NOTIFICATION_DURATION: 5000, // Длительность показа информационных уведомлений в мс
        MEDIA_LOADING_TIMEOUT: 30000, // Таймаут загрузки медиа в мс
        AUTO_SCROLL: true, // Автопрокрутка транскрипта по умолчанию
        SHOW_TIMESTAMPS: true // Показывать временные метки по умолчанию
    },

    // Настройки транскрипции по умолчанию (соответствуют src/config/settings.py)
    TRANSCRIPTION: {
        DEFAULT_MODEL: 'large-v3',
        DEFAULT_LANGUAGE: 'ru',
        DEFAULT_DIARIZE: true,  // Включено по умолчанию на сервере
        DEFAULT_COMPUTE_TYPE: 'float16',  // Захардкожено на сервере
        DEFAULT_BATCH_SIZE: 4,  // Соответствует серверу
        MODELS: [
            { value: 'large-v3', label: 'Large-v3 (лучшее качество)' },
            { value: 'medium', label: 'Medium (быстрее)' },
            { value: 'small', label: 'Small (самый быстрый)' }
        ],
        LANGUAGES: [
            { value: 'ru', label: 'Русский' },
            { value: 'en', label: 'English' },
            { value: 'auto', label: 'Автоопределение' }
        ]
    },

    // Настройки суммаризации перенесены в переменные окружения сервера
    // Конфигурация теперь получается через API: /api/config/summarization

    // Поддерживаемые форматы файлов
    FILE_FORMATS: {
        AUDIO: ['mp3', 'm4a', 'wav', 'flac', 'ogg', 'wma', 'aac', 'opus'],
        VIDEO: ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', '3gp', 'mts'],
        EXPORT: ['json', 'srt', 'vtt', 'tsv', 'docx', 'pdf']
    },

    // Настройки экспорта
    EXPORT: {
        FORMATS: {
            json: { label: 'JSON', icon: 'fas fa-download' },
            srt: { label: 'SRT', icon: 'fas fa-download' },
            vtt: { label: 'VTT', icon: 'fas fa-download' },
            tsv: { label: 'TSV', icon: 'fas fa-download' },
            docx: { label: 'DOCX', icon: 'fas fa-file-word' },
            pdf: { label: 'PDF', icon: 'fas fa-file-pdf' }
        }
    },

    // Цвета для спикеров
    SPEAKER_COLORS: [
        '#4CAF50', // Зеленый
        '#FF9800', // Оранжевый
        '#9C27B0', // Фиолетовый
        '#2196F3', // Синий
        '#F44336', // Красный
        '#795548', // Коричневый
        '#607D8B', // Серо-синий
        '#E91E63'  // Розовый
    ],

    // Сообщения интерфейса
    MESSAGES: {
        ERRORS: {
            NO_FILE_SELECTED: 'Пожалуйста, выберите файл для транскрипции',
            FILE_UPLOAD_ERROR: 'Ошибка загрузки файла',
            TRANSCRIPTION_NOT_COMPLETED: 'Транскрипция не завершена или повреждена',
            DOWNLOAD_ERROR: 'Ошибка скачивания файла',
            NETWORK_ERROR: 'Ошибка подключения к серверу. Проверьте интернет-соединение.',
            FILE_NOT_FOUND: 'Файл не найден на сервере.',
            DELETE_ERROR: 'Ошибка удаления транскрипции',
            LOAD_HISTORY_ERROR: 'Ошибка загрузки истории',
            LOAD_TRANSCRIPTION_ERROR: 'Ошибка загрузки транскрипции'
        },
        SUCCESS: {
            TRANSCRIPTION_DELETED: 'Транскрипция успешно удалена',
            FILE_DOWNLOADED: 'Готово'
        },
        INFO: {
            TRANSCRIPTION_CANCELLED: 'Транскрипция отменена',
            MEDIA_LOADING_SKIPPED: 'Загрузка медиа пропущена. Показан только транскрипт.',
            MEDIA_LOAD_ERROR: 'Медиа файл не удалось загрузить, но транскрипт доступен для просмотра',
            LARGE_FILE_WARNING: 'Большие файлы могут загружаться несколько минут...'
        },
        PROGRESS: {
            PREPARING: 'Подготовка к обработке...',
            LOADING_MODELS: 'Загрузка моделей...',
            LOADING_AUDIO: 'Загрузка аудио...',
            TRANSCRIBING: 'Выполнение транскрипции...',
            ALIGNING: 'Выравнивание текста...',
            DIARIZING: 'Диаризация спикеров...',
            SAVING: 'Сохранение результатов...',
            PROCESSING: 'Обработка...'
        }
    },

    // Настройки разработки
    DEBUG: {
        ENABLED: true, // Включить отладочные сообщения
        LOG_API_CALLS: true, // Логировать API вызовы
        SIMULATE_SLOW_NETWORK: false // Симулировать медленную сеть
    }
};

// Экспортируем конфигурацию для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
} 
// Модуль для работы с API
class ApiManager {
    constructor() {
        this.config = CONFIG.API;
        this.baseUrl = this.config.BASE_URL;
        // HF_TOKEN больше не передается из клиента - сервер берет его из переменных окружения
    }

    // Загрузка файла для транскрипции
    async uploadFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        const params = new URLSearchParams({
            model: options.model || CONFIG.TRANSCRIPTION.DEFAULT_MODEL,
            language: options.language || CONFIG.TRANSCRIPTION.DEFAULT_LANGUAGE,
            diarize: options.diarize || CONFIG.TRANSCRIPTION.DEFAULT_DIARIZE,
            // hf_token больше не передается - сервер автоматически использует токен из переменных окружения
            compute_type: options.compute_type || CONFIG.TRANSCRIPTION.DEFAULT_COMPUTE_TYPE,
            batch_size: options.batch_size || CONFIG.TRANSCRIPTION.DEFAULT_BATCH_SIZE
        });
        
        const response = await fetch(`${this.baseUrl}${this.config.ENDPOINTS.UPLOAD}?${params}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    // Получение статуса транскрипции
    async getStatus(taskId) {
        const response = await fetch(`${this.baseUrl}${this.config.ENDPOINTS.STATUS}/${taskId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    // Получение списка транскрипций
    async getTranscriptions() {
        const url = `${this.baseUrl}${this.config.ENDPOINTS.TRANSCRIPTIONS}`;
        
        if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
            console.log(`API: Getting transcriptions from: ${url}`);
        }
        
        try {
            const response = await fetch(url);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`API Error: ${response.status} - ${errorText}`);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            
            if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
                console.log(`API: Got ${data.length} transcriptions`);
            }
            
            return data;
        } catch (error) {
            console.error('API: Failed to fetch transcriptions:', error);
            throw error;
        }
    }

    // Получение S3 ссылок
    async getS3Links(taskId) {
        const url = `${this.baseUrl}${this.config.ENDPOINTS.S3_LINKS}/${taskId}`;
        
        if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
            console.log(`[API] Получение S3 ссылок для задачи: ${taskId}`);
            console.log(`[API] URL запроса: ${url}`);
        }
        
        try {
            const response = await fetch(url);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[API] Ошибка получения S3 ссылок: ${response.status} - ${errorText}`);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            
            if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
                console.log(`[API] Получены S3 ссылки:`, data);
            }
            
            // Возвращаем только s3_links из ответа
            return data.s3_links || {};
            
        } catch (error) {
            console.error('[API] Ошибка при получении S3 ссылок:', error);
            throw error;
        }
    }

    // Скачивание файла
    async downloadFile(taskId, format) {
        let endpoint;
        
        // Логируем запрос если включен debug
        if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
            console.log(`API: Downloading file - TaskID: ${taskId}, Format: ${format}`);
        }
        
        switch (format) {
            case 'json':
            case 'docx':
            case 'pdf':
                endpoint = `${this.config.ENDPOINTS.DOWNLOAD_TRANSCRIPT}/${taskId}?format_type=${format}`;
                break;
            case 'srt':
            case 'vtt':
            case 'tsv':
                endpoint = `${this.config.ENDPOINTS.DOWNLOAD_SUBTITLE}/${taskId}?format_type=${format}`;
                break;
            default:
                throw new Error(`Неподдерживаемый формат: ${format}`);
        }
        
        const url = `${this.baseUrl}${endpoint}`;
        
        if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
            console.log(`API: Making request to: ${url}`);
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`API Error: ${response.status} - ${errorText}`);
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }
        
        return response;
    }

    // Скачивание аудио файла
    async downloadAudio(taskId) {
        const response = await fetch(`${this.baseUrl}${this.config.ENDPOINTS.DOWNLOAD_AUDIO}/${taskId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response;
    }

    // Удаление транскрипции
    async deleteTranscription(taskId) {
        const response = await fetch(`${this.baseUrl}${this.config.ENDPOINTS.DELETE_TRANSCRIPTION}/${taskId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    // Отмена транскрипции
    async cancelTranscription(taskId) {
        const response = await fetch(`${this.baseUrl}${this.config.ENDPOINTS.STATUS}/${taskId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    // Загрузка файла с прогрессом
    downloadFileWithProgress(url, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            xhr.open('GET', url, true);
            xhr.responseType = 'blob';
            
            xhr.onprogress = function(event) {
                if (event.lengthComputable && onProgress) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    onProgress(percentComplete);
                }
            };
            
            xhr.onload = function() {
                if (xhr.status === 200) {
                    resolve(xhr.response);
                } else {
                    reject(new Error(`HTTP error! status: ${xhr.status}`));
                }
            };
            
            xhr.onerror = function() {
                reject(new Error('Network error'));
            };
            
            xhr.send();
        });
    }

    // Универсальный метод для API запросов
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const requestOptions = {
            ...defaultOptions,
            ...options
        };
        
        // Если передан body и это не FormData, конвертируем в JSON
        if (requestOptions.body && !(requestOptions.body instanceof FormData)) {
            requestOptions.body = JSON.stringify(requestOptions.body);
        }
        
        if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
            console.log(`[API] Making request to: ${url}`, requestOptions);
        }
        
        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[API] Error: ${response.status} - ${errorText}`);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            
            if (CONFIG.DEBUG && CONFIG.DEBUG.LOG_API_CALLS) {
                console.log(`[API] Response received:`, data);
            }
            
            return data;
            
        } catch (error) {
            console.error('[API] Request failed:', error);
            throw error;
        }
    }
}

// Экспорт для использования в других модулях
window.ApiManager = ApiManager; 
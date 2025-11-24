// Модуль для работы с историей транскрипций
class HistoryManager {
    constructor(apiManager, uiManager) {
        this.apiManager = apiManager;
        this.uiManager = uiManager;
        this.transcriptions = [];
        this.onHistoryItemClick = null;
    }

    // Загрузка истории транскрипций
    async loadTranscriptionHistory() {
        try {
            const historyList = document.getElementById('historyList');
            if (historyList) {
                this.uiManager.showLoading('historyList', 'Загрузка истории...');
            }

            const transcriptions = await this.apiManager.getTranscriptions();
            this.transcriptions = transcriptions;
            this.displayHistory(transcriptions);

        } catch (error) {
            console.error('Ошибка загрузки истории:', error);
            this.uiManager.showError(`${CONFIG.MESSAGES.ERRORS.LOAD_HISTORY_ERROR}: ${error.message}`);
            
            const historyList = document.getElementById('historyList');
            if (historyList) {
                historyList.innerHTML = '<p class="error-message">Ошибка загрузки истории</p>';
            }
        }
    }

    // Отображение истории
    displayHistory(transcriptions) {
        const historyList = document.getElementById('historyList');
        if (!historyList) return;

        if (!transcriptions || transcriptions.length === 0) {
            historyList.innerHTML = '<p class="empty-message">История транскрипций пуста</p>';
            return;
        }

        historyList.innerHTML = '';

        // Сортировка по дате (новые сначала)
        const sortedTranscriptions = transcriptions.sort((a, b) => {
            return new Date(b.created_at) - new Date(a.created_at);
        });

        // Группируем транскрипции по статусу
        const categories = [
            {
                title: 'Завершенные',
                icon: 'fa-check-circle',
                description: 'Готовые транскрипции для просмотра',
                status: 'completed',
                color: '#4caf50'
            },
            {
                title: 'В обработке',
                icon: 'fa-spinner',
                description: 'Транскрипции в процессе обработки',
                status: 'processing',
                color: '#ff9800'
            },
            {
                title: 'Ожидание',
                icon: 'fa-clock',
                description: 'Транскрипции в очереди на обработку',
                status: 'pending',
                color: '#2196f3'
            },
            {
                title: 'Ошибки',
                icon: 'fa-exclamation-triangle',
                description: 'Транскрипции с ошибками',
                status: ['failed', 'error'],
                color: '#f44336'
            }
        ];

        categories.forEach(category => {
            const categoryTranscriptions = sortedTranscriptions.filter(t => {
                if (Array.isArray(category.status)) {
                    return category.status.includes(t.status);
                }
                return t.status === category.status;
            });

            if (categoryTranscriptions.length > 0) {
                const categorySection = this.createHistoryCategory(category, categoryTranscriptions);
                historyList.appendChild(categorySection);
            }
        });
    }

    // Создание категории истории
    createHistoryCategory(category, transcriptions) {
        const section = document.createElement('div');
        section.className = 'history-category';
        
        section.innerHTML = `
            <div class="category-header">
                <div class="category-icon" style="background: linear-gradient(135deg, ${category.color}, ${this.adjustColor(category.color, -20)})">
                    <i class="fas ${category.icon}"></i>
                </div>
                <div class="category-info">
                    <h4 class="category-title">${category.title} (${transcriptions.length})</h4>
                    <p class="category-description">${category.description}</p>
                </div>
            </div>
            <div class="category-items">
                ${transcriptions.map(transcription => this.createHistoryItem(transcription)).join('')}
            </div>
        `;
        
        return section;
    }

    // Создание элемента истории в новом стиле
    createHistoryItem(transcription) {
        const statusClass = this.getStatusClass(transcription.status);
        const statusIcon = this.getStatusIcon(transcription.status);
        const statusText = this.getStatusText(transcription.status);
        
        // Улучшаем отображение имени файла
        let displayFilename = transcription.filename || 'Неизвестный файл';
        if (displayFilename === 'processing...' || displayFilename === 'pending...') {
            displayFilename = `Файл в обработке (ID: ${transcription.id.substring(0, 8)}...)`;
        }

        return `
            <div class="category-item history-item-wrapper" data-task-id="${transcription.id}">
                <div class="item-info">
                    <div class="item-icon">
                        <i class="fas fa-file-audio"></i>
                    </div>
                    <div class="item-details">
                        <span class="item-name">${displayFilename}</span>
                        <div class="item-meta">
                            <span class="meta-item">
                                <i class="fas fa-calendar"></i>
                                ${this.formatDate(transcription.created_at)}
                            </span>
                            ${transcription.model ? `
                                <span class="meta-item">
                                    <i class="fas fa-brain"></i>
                                    ${transcription.model}
                                </span>
                            ` : ''}
                            ${transcription.language ? `
                                <span class="meta-item">
                                    <i class="fas fa-language"></i>
                                    ${transcription.language}
                                </span>
                            ` : ''}
                            ${transcription.duration ? `
                                <span class="meta-item">
                                    <i class="fas fa-clock"></i>
                                    ${this.uiManager.formatTime(transcription.duration)}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div class="item-status">
                    <span class="status-badge ${statusClass}">
                        <i class="fas ${statusIcon}"></i>
                        ${statusText}
                    </span>
                </div>
                <div class="item-actions">
                    ${transcription.status === 'completed' ? `
                        <button class="btn btn-primary btn-compact" onclick="window.historyManager?.handleHistoryItemClick('${transcription.id}', '${transcription.status}')" title="Открыть транскрипцию">
                            <i class="fas fa-eye"></i>
                        </button>
                    ` : ''}
                    <button class="btn btn-outline btn-compact" onclick="window.historyManager?.confirmDeleteTranscription('${transcription.id}', '${displayFilename}')" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="history-item-loading" id="historyLoading_${transcription.id}" style="display: none;">
                    <div class="loading-spinner">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>Загрузка...</span>
                    </div>
                </div>
            </div>
        `;
    }

    // Вспомогательная функция для изменения цвета
    adjustColor(color, amount) {
        const usePound = color[0] === '#';
        const col = usePound ? color.slice(1) : color;
        const num = parseInt(col, 16);
        let r = (num >> 16) + amount;
        let g = (num >> 8 & 0x00FF) + amount;
        let b = (num & 0x0000FF) + amount;
        r = r > 255 ? 255 : r < 0 ? 0 : r;
        g = g > 255 ? 255 : g < 0 ? 0 : g;
        b = b > 255 ? 255 : b < 0 ? 0 : b;
        return (usePound ? '#' : '') + (r << 16 | g << 8 | b).toString(16).padStart(6, '0');
    }

    // Получение класса статуса
    getStatusClass(status) {
        switch (status) {
            case 'completed':
                return 'status-completed';
            case 'failed':
            case 'error':
                return 'status-error';
            case 'pending':
            case 'processing':
                return 'status-processing';
            default:
                return 'status-unknown';
        }
    }

    // Получение иконки статуса
    getStatusIcon(status) {
        switch (status) {
            case 'completed':
                return 'fa-check-circle';
            case 'failed':
            case 'error':
                return 'fa-times-circle';
            case 'pending':
            case 'processing':
                return 'fa-spinner fa-spin';
            default:
                return 'fa-question-circle';
        }
    }

    // Получение текста статуса
    getStatusText(status) {
        switch (status) {
            case 'completed':
                return 'Завершено';
            case 'failed':
                return 'Ошибка';
            case 'error':
                return 'Ошибка';
            case 'pending':
                return 'Ожидание';
            case 'processing':
                return 'Обработка';
            default:
                return 'Неизвестно';
        }
    }

    // Форматирование даты
    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) {
            return 'Сегодня, ' + date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        } else if (diffDays === 2) {
            return 'Вчера, ' + date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        } else if (diffDays <= 7) {
            return `${diffDays - 1} дн. назад`;
        } else {
            return date.toLocaleDateString('ru-RU', { 
                day: '2-digit', 
                month: '2-digit', 
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    // Обработка клика по элементу истории
    handleHistoryItemClick(taskId, status) {
        if (status !== 'completed') {
            this.uiManager.showError('Транскрипция не завершена');
            return;
        }

        if (this.onHistoryItemClick && typeof this.onHistoryItemClick === 'function') {
            this.onHistoryItemClick(taskId, status);
        }
    }

    // Показать загрузку для элемента истории
    showHistoryItemLoading(taskId) {
        const loadingElement = document.getElementById(`historyLoading_${taskId}`);
        const contentElement = document.querySelector(`[data-task-id="${taskId}"] .history-item-content`);
        
        if (loadingElement) {
            loadingElement.style.display = 'block';
        }
        if (contentElement) {
            contentElement.style.opacity = '0.5';
        }
    }

    // Скрыть загрузку для элемента истории
    hideHistoryItemLoading(taskId) {
        const loadingElement = document.getElementById(`historyLoading_${taskId}`);
        const contentElement = document.querySelector(`[data-task-id="${taskId}"] .history-item-content`);
        
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
        if (contentElement) {
            contentElement.style.opacity = '1';
        }
    }

    // Подтверждение удаления транскрипции
    confirmDeleteTranscription(taskId, filename) {
        this.showDeleteConfirmModal(taskId, filename);
    }

    // Показать модальное окно подтверждения удаления
    showDeleteConfirmModal(taskId, filename) {
        let modal = document.getElementById('deleteConfirmModal');
        
        if (!modal) {
            modal = this.createDeleteConfirmModal();
            document.body.appendChild(modal);
        }
        
        const filenameElement = modal.querySelector('#deleteFilename');
        const confirmButton = modal.querySelector('#confirmDeleteBtn');
        
        if (filenameElement) {
            filenameElement.textContent = filename;
        }
        
        if (confirmButton) {
            confirmButton.onclick = () => this.deleteTranscription(taskId);
        }
        
        modal.style.display = 'flex';
    }

    // Создать модальное окно подтверждения удаления
    createDeleteConfirmModal() {
        const modal = document.createElement('div');
        modal.id = 'deleteConfirmModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3><i class="fas fa-exclamation-triangle"></i> Подтверждение удаления</h3>
                    <button class="modal-close" onclick="window.historyManager?.closeDeleteModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <p>Вы уверены, что хотите удалить транскрипцию файла <strong id="deleteFilename"></strong>?</p>
                    <p class="warning-text">Это действие нельзя отменить.</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline" onclick="window.historyManager?.closeDeleteModal()">Отмена</button>
                    <button class="btn btn-danger" id="confirmDeleteBtn">
                        <i class="fas fa-trash"></i> Удалить
                    </button>
                </div>
            </div>
        `;
        return modal;
    }

    // Закрыть модальное окно удаления
    closeDeleteModal() {
        const modal = document.getElementById('deleteConfirmModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Удаление транскрипции
    async deleteTranscription(taskId) {
        try {
            this.closeDeleteModal();
            
            // Показать загрузку
            this.showHistoryItemLoading(taskId);
            
            await this.apiManager.deleteTranscription(taskId);
            
            // Удалить элемент из DOM
            const historyItem = document.querySelector(`[data-task-id="${taskId}"]`);
            if (historyItem) {
                historyItem.remove();
            }
            
            // Обновить локальный массив
            this.transcriptions = this.transcriptions.filter(t => t.id !== taskId);
            
            // Показать сообщение об успехе
            this.uiManager.showSuccessMessage(CONFIG.MESSAGES.SUCCESS.TRANSCRIPTION_DELETED);
            
            // Если история пуста, показать соответствующее сообщение
            if (this.transcriptions.length === 0) {
                const historyList = document.getElementById('historyList');
                if (historyList) {
                    historyList.innerHTML = '<p class="empty-message">История транскрипций пуста</p>';
                }
            }
            
        } catch (error) {
            console.error('Ошибка удаления транскрипции:', error);
            this.hideHistoryItemLoading(taskId);
            this.uiManager.showError(`${CONFIG.MESSAGES.ERRORS.DELETE_ERROR}: ${error.message}`);
        }
    }

    // Обновление истории (добавление новой транскрипции)
    addTranscription(transcription) {
        this.transcriptions.unshift(transcription); // Добавить в начало
        this.displayHistory(this.transcriptions);
    }

    // Обновление статуса транскрипции
    updateTranscriptionStatus(taskId, updatedData) {
        const transcription = this.transcriptions.find(t => t.id === taskId);
        if (transcription) {
            // Обновляем все переданные поля
            Object.assign(transcription, updatedData);
            
            // Обновляем конкретный элемент в DOM вместо перерисовки всей истории
            this.updateHistoryItemInDOM(taskId, transcription);
        }
    }
    
    // Обновление конкретного элемента истории в DOM
    updateHistoryItemInDOM(taskId, transcription) {
        const historyItem = document.querySelector(`[data-task-id="${taskId}"]`);
        if (!historyItem) return;
        
        const statusClass = this.getStatusClass(transcription.status);
        const statusIcon = this.getStatusIcon(transcription.status);
        const statusText = this.getStatusText(transcription.status);
        
        // Улучшаем отображение имени файла
        let displayFilename = transcription.filename || 'Неизвестный файл';
        if (displayFilename === 'processing...' || displayFilename === 'pending...') {
            displayFilename = `Файл в обработке (ID: ${transcription.id.substring(0, 8)}...)`;
        }
        
        // Обновляем статус
        const statusElement = historyItem.querySelector('.history-item-status');
        if (statusElement) {
            statusElement.className = `history-item-status ${statusClass}`;
            statusElement.innerHTML = `
                <i class="fas ${statusIcon}"></i>
                <span>${statusText}</span>
            `;
        }
        
        // Обновляем имя файла
        const filenameElement = historyItem.querySelector('.filename');
        if (filenameElement) {
            filenameElement.textContent = displayFilename;
        }
        
        // Обновляем информацию о прогрессе
        const infoContainer = historyItem.querySelector('.history-item-info');
        if (infoContainer) {
            // Удаляем старый элемент прогресса если есть
            const oldProgressElement = infoContainer.querySelector('.progress-info');
            if (oldProgressElement) {
                oldProgressElement.remove();
            }
            
            // Добавляем новый элемент прогресса если статус processing
            if (transcription.progress && transcription.status === 'processing') {
                const progressElement = document.createElement('span');
                progressElement.className = 'info-item progress-info';
                progressElement.innerHTML = `
                    <i class="fas fa-spinner fa-spin"></i>
                    ${transcription.progress}
                `;
                infoContainer.appendChild(progressElement);
            }
        }
        
        // Обновляем кнопки действий
        const actionsContainer = historyItem.querySelector('.history-item-actions');
        if (actionsContainer) {
            actionsContainer.innerHTML = `
                ${transcription.status === 'completed' ? `
                    <button class="btn btn-small btn-primary" onclick="window.historyManager?.handleHistoryItemClick('${transcription.id}', '${transcription.status}')">
                        <i class="fas fa-eye"></i> Просмотр
                    </button>
                ` : ''}
                <button class="btn btn-small btn-danger" onclick="window.historyManager?.confirmDeleteTranscription('${transcription.id}', '${displayFilename}')">
                    <i class="fas fa-trash"></i> Удалить
                </button>
            `;
        }
    }

    // Получение транскрипции по ID
    getTranscriptionById(taskId) {
        return this.transcriptions.find(t => t.id === taskId);
    }

    // Установка callback для клика по элементу истории
    setOnHistoryItemClickCallback(callback) {
        this.onHistoryItemClick = callback;
    }

    // Очистка истории
    clearHistory() {
        this.transcriptions = [];
        const historyList = document.getElementById('historyList');
        if (historyList) {
            historyList.innerHTML = '<p class="empty-message">История транскрипций пуста</p>';
        }
    }
}

// Экспорт для использования в других модулях
window.HistoryManager = HistoryManager; 
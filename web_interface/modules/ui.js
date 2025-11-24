// Модуль для управления интерфейсом
class UIManager {
    constructor() {
        this.config = CONFIG.UI;
        this.initializeEventListeners();
    }

    // Инициализация общих обработчиков событий
    initializeEventListeners() {
        // Обработчик клавиши Escape для закрытия модальных окон
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeModal();
                this.closeDeleteModal();
            }
        });
    }

    // Показать ошибку
    showError(message) {
        const modal = document.getElementById('errorModal');
        const errorMessage = document.getElementById('errorMessage');
        
        if (modal && errorMessage) {
            errorMessage.textContent = message;
            modal.style.display = 'flex';
        } else {
            // Fallback если модальное окно не найдено
            alert(`Ошибка: ${message}`);
        }
    }

    // Закрыть модальное окно ошибки
    closeModal() {
        const modal = document.getElementById('errorModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Показать сообщение об успехе
    showSuccessMessage(message) {
        this.showNotification(message, 'success', this.config.NOTIFICATION_DURATION);
    }

    // Показать информационное сообщение
    showInfoMessage(message) {
        this.showNotification(message, 'info', this.config.INFO_NOTIFICATION_DURATION);
    }

    // Показать уведомление
    showNotification(message, type = 'info', duration = 3000) {
        // Создаем элемент уведомления
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">&times;</button>
            </div>
        `;

        // Добавляем стили если их нет
        this.ensureNotificationStyles();

        // Добавляем в DOM
        document.body.appendChild(notification);

        // Показываем с анимацией
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Автоматически скрываем
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
    }

    // Получить иконку для уведомления
    getNotificationIcon(type) {
        switch (type) {
            case 'success':
                return 'fa-check-circle';
            case 'error':
                return 'fa-exclamation-triangle';
            case 'info':
                return 'fa-info-circle';
            case 'warning':
                return 'fa-exclamation-circle';
            default:
                return 'fa-info-circle';
        }
    }

    // Добавить стили для уведомлений если их нет
    ensureNotificationStyles() {
        if (document.getElementById('notification-styles')) {
            return;
        }

        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 10000;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                max-width: 400px;
                border-left: 4px solid #007bff;
            }
            .notification.show {
                transform: translateX(0);
            }
            .notification-success {
                border-left-color: #28a745;
            }
            .notification-error {
                border-left-color: #dc3545;
            }
            .notification-warning {
                border-left-color: #ffc107;
            }
            .notification-content {
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .notification-content i {
                font-size: 18px;
                color: #007bff;
            }
            .notification-success .notification-content i {
                color: #28a745;
            }
            .notification-error .notification-content i {
                color: #dc3545;
            }
            .notification-warning .notification-content i {
                color: #ffc107;
            }
            .notification-content span {
                flex: 1;
                font-size: 14px;
                line-height: 1.4;
            }
            .notification-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                color: #666;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .notification-close:hover {
                color: #333;
            }
        `;
        document.head.appendChild(styles);
    }

    // Сброс интерфейса
    resetInterface() {
        // Скрыть все секции
        const sections = ['progressSection', 'resultsSection'];
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'none';
            }
        });

        // Показать секцию загрузки
        const uploadSection = document.getElementById('uploadSection');
        if (uploadSection) {
            uploadSection.style.display = 'block';
        }

        // Очистить содержимое транскрипта
        const transcriptContent = document.getElementById('transcriptContent');
        if (transcriptContent) {
            transcriptContent.innerHTML = '';
        }

        // Очистить медиаплееры
        const audioPlayer = document.getElementById('audioPlayer');
        const videoPlayer = document.getElementById('videoPlayer');
        
        if (audioPlayer) {
            audioPlayer.src = '';
            audioPlayer.style.display = 'none';
        }
        
        if (videoPlayer) {
            videoPlayer.src = '';
            videoPlayer.style.display = 'none';
        }

        // Очистить S3 ссылки
        const downloadsCollapsible = document.getElementById('downloadsCollapsible');
        const s3LinksGrid = document.getElementById('s3LinksGrid');
        
        if (downloadsCollapsible) {
            downloadsCollapsible.style.display = 'none';
            // Убираем класс expanded если он есть
            downloadsCollapsible.classList.remove('expanded');
        }
        
        if (s3LinksGrid) {
            s3LinksGrid.innerHTML = '';
        }

        // Сбросить прогресс
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        if (progressFill) {
            progressFill.style.width = '0%';
        }
        
        if (progressText) {
            progressText.textContent = CONFIG.MESSAGES.PROGRESS.PREPARING;
        }
    }

    // Показать загрузку
    showLoading(elementId, text = 'Загрузка...') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="loading-spinner">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>${text}</span>
                </div>
            `;
        }
    }

    // Скрыть загрузку
    hideLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '';
        }
    }

    // Форматирование времени
    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
    }

    // Создание элемента загрузки
    createLoadingElement(text = 'Загрузка...') {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-container';
        loadingDiv.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                <span>${text}</span>
            </div>
        `;
        return loadingDiv;
    }

    // Показать/скрыть элемент
    toggleElement(elementId, show = null) {
        const element = document.getElementById(elementId);
        if (element) {
            if (show === null) {
                element.style.display = element.style.display === 'none' ? 'block' : 'none';
            } else {
                element.style.display = show ? 'block' : 'none';
            }
        }
    }

    // Закрыть модальное окно удаления
    closeDeleteModal() {
        const modal = document.getElementById('deleteConfirmModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Добавить класс к элементу
    addClass(elementId, className) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.add(className);
        }
    }

    // Удалить класс у элемента
    removeClass(elementId, className) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove(className);
        }
    }

    // Переключить класс у элемента
    toggleClass(elementId, className) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.toggle(className);
        }
    }
}

// Экспорт для использования в других модулях
window.UIManager = UIManager; 
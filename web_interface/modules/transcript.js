// Модуль для работы с транскриптом
class TranscriptManager {
    constructor(uiManager) {
        this.uiManager = uiManager;
        this.currentTranscript = null;
        this.autoScroll = CONFIG.UI.AUTO_SCROLL;
        this.showTimestamps = CONFIG.UI.SHOW_TIMESTAMPS;
        this.currentHighlightedSegment = null;
    }

    // Инициализация обработчиков событий
    initializeEventListeners() {
        const toggleAutoScrollBtn = document.getElementById('toggleAutoScroll');
        const toggleTimestampsBtn = document.getElementById('toggleTimestamps');
        
        if (toggleAutoScrollBtn) {
            toggleAutoScrollBtn.addEventListener('click', () => this.toggleAutoScroll());
        }
        
        if (toggleTimestampsBtn) {
            toggleTimestampsBtn.addEventListener('click', () => this.toggleTimestamps());
        }
    }

    // Отображение транскрипта
    displayTranscript(segments) {
        if (!segments || !Array.isArray(segments)) {
            console.error('Некорректные данные транскрипта');
            return;
        }

        this.currentTranscript = segments;
        const transcriptContent = document.getElementById('transcriptContent');
        
        if (!transcriptContent) {
            console.error('Элемент transcriptContent не найден');
            return;
        }

        transcriptContent.innerHTML = '';

        segments.forEach((segment, index) => {
            const segmentElement = this.createSegmentElement(segment, index);
            transcriptContent.appendChild(segmentElement);
        });

        // Обновить состояние кнопок
        this.updateControlButtons();
    }

    // Создание элемента сегмента
    createSegmentElement(segment, index) {
        const segmentDiv = document.createElement('div');
        segmentDiv.className = 'transcript-segment';
        segmentDiv.dataset.start = segment.start;
        segmentDiv.dataset.end = segment.end;
        segmentDiv.dataset.index = index;

        // Добавляем CSS класс для спикера (включая SPEAKER_00)
        if (segment.speaker) {
            const speakerIndex = parseInt(segment.speaker.replace('SPEAKER_', '')) || 0;
            segmentDiv.classList.add(`speaker-${speakerIndex}`);
        }

        // Обработчик клика для перехода к времени
        segmentDiv.addEventListener('click', () => {
            if (window.mediaPlayerManager) {
                window.mediaPlayerManager.setCurrentTime(segment.start);
            }
        });

        let content = '';

        // Временная метка (если включена)
        if (this.showTimestamps) {
            const timeSpan = document.createElement('span');
            timeSpan.className = 'timestamp';
            timeSpan.textContent = this.uiManager.formatTime(segment.start);
            content += timeSpan.outerHTML;
        }

        // Текст с поддержкой спикеров (теперь показываем всех спикеров)
        if (segment.speaker) {
            const speakerSpan = document.createElement('span');
            speakerSpan.className = 'speaker';
            speakerSpan.style.color = this.getSpeakerColor(segment.speaker);
            speakerSpan.textContent = `${segment.speaker}: `;
            content += speakerSpan.outerHTML;
        }

        const textSpan = document.createElement('span');
        textSpan.className = 'text';
        textSpan.textContent = segment.text;
        content += textSpan.outerHTML;

        segmentDiv.innerHTML = content;
        return segmentDiv;
    }

    // Получение цвета для спикера
    getSpeakerColor(speaker) {
        const speakerIndex = parseInt(speaker.replace('SPEAKER_', '')) || 0;
        return CONFIG.SPEAKER_COLORS[speakerIndex % CONFIG.SPEAKER_COLORS.length];
    }

    // Обновление подсветки транскрипта
    updateTranscriptHighlight(currentTime) {
        if (!this.currentTranscript) return;

        const segments = document.querySelectorAll('.transcript-segment');
        let activeSegment = null;

        segments.forEach(segment => {
            const start = parseFloat(segment.dataset.start);
            const end = parseFloat(segment.dataset.end);

            if (currentTime >= start && currentTime <= end) {
                segment.classList.add('active');
                activeSegment = segment;
            } else {
                segment.classList.remove('active');
            }
        });

        // Автопрокрутка к активному сегменту
        if (this.autoScroll && activeSegment && activeSegment !== this.currentHighlightedSegment) {
            this.scrollToSegment(activeSegment);
            this.currentHighlightedSegment = activeSegment;
        }
    }

    // Прокрутка к сегменту
    scrollToSegment(segment) {
        const transcriptContent = document.getElementById('transcriptContent');
        if (transcriptContent && segment) {
            const containerRect = transcriptContent.getBoundingClientRect();
            const segmentRect = segment.getBoundingClientRect();
            
            // Проверяем, виден ли сегмент
            const isVisible = segmentRect.top >= containerRect.top && 
                             segmentRect.bottom <= containerRect.bottom;
            
            if (!isVisible) {
                segment.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }
    }

    // Переключение автопрокрутки
    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        this.updateControlButtons();
        
        const message = this.autoScroll ? 'Автопрокрутка включена' : 'Автопрокрутка отключена';
        this.uiManager.showInfoMessage(message);
    }

    // Переключение временных меток
    toggleTimestamps() {
        this.showTimestamps = !this.showTimestamps;
        this.updateControlButtons();
        
        // Обновить отображение транскрипта
        if (this.currentTranscript) {
            this.displayTranscript(this.currentTranscript);
        }
        
        const message = this.showTimestamps ? 'Временные метки показаны' : 'Временные метки скрыты';
        this.uiManager.showInfoMessage(message);
    }

    // Обновление состояния кнопок управления
    updateControlButtons() {
        const autoScrollBtn = document.getElementById('toggleAutoScroll');
        const timestampsBtn = document.getElementById('toggleTimestamps');
        
        if (autoScrollBtn) {
            if (this.autoScroll) {
                autoScrollBtn.classList.add('active');
                autoScrollBtn.innerHTML = '<i class="fas fa-arrows-alt-v"></i> Авто-прокрутка (вкл)';
            } else {
                autoScrollBtn.classList.remove('active');
                autoScrollBtn.innerHTML = '<i class="fas fa-arrows-alt-v"></i> Авто-прокрутка (выкл)';
            }
        }
        
        if (timestampsBtn) {
            if (this.showTimestamps) {
                timestampsBtn.classList.add('active');
                timestampsBtn.innerHTML = '<i class="fas fa-clock"></i> Временные метки (вкл)';
            } else {
                timestampsBtn.classList.remove('active');
                timestampsBtn.innerHTML = '<i class="fas fa-clock"></i> Временные метки (выкл)';
            }
        }
    }

    // Поиск по транскрипту
    searchInTranscript(query) {
        if (!this.currentTranscript || !query) return [];

        const results = [];
        this.currentTranscript.forEach((segment, index) => {
            if (segment.text.toLowerCase().includes(query.toLowerCase())) {
                results.push({
                    index,
                    segment,
                    start: segment.start,
                    text: segment.text
                });
            }
        });

        return results;
    }

    // Переход к сегменту по индексу
    goToSegment(index) {
        if (!this.currentTranscript || index < 0 || index >= this.currentTranscript.length) {
            return;
        }

        const segment = this.currentTranscript[index];
        if (window.mediaPlayerManager) {
            window.mediaPlayerManager.setCurrentTime(segment.start);
        }

        // Подсветить сегмент
        const segmentElement = document.querySelector(`[data-index="${index}"]`);
        if (segmentElement) {
            this.scrollToSegment(segmentElement);
            segmentElement.classList.add('highlighted');
            
            // Убрать подсветку через 2 секунды
            setTimeout(() => {
                segmentElement.classList.remove('highlighted');
            }, 2000);
        }
    }

    // Экспорт транскрипта в текстовом формате
    exportAsText(includeTimestamps = true, includeSpeakers = true) {
        if (!this.currentTranscript) return '';

        return this.currentTranscript.map(segment => {
            let line = '';
            
            if (includeTimestamps) {
                line += `[${this.uiManager.formatTime(segment.start)}] `;
            }
            
            if (includeSpeakers && segment.speaker) {
                line += `${segment.speaker}: `;
            }
            
            line += segment.text;
            return line;
        }).join('\n');
    }

    // Получение статистики транскрипта
    getTranscriptStats() {
        if (!this.currentTranscript) return null;

        const totalDuration = this.currentTranscript.length > 0 ? 
            this.currentTranscript[this.currentTranscript.length - 1].end : 0;
        
        const totalWords = this.currentTranscript.reduce((count, segment) => {
            return count + segment.text.split(' ').length;
        }, 0);

        const speakers = new Set();
        this.currentTranscript.forEach(segment => {
            if (segment.speaker) {
                speakers.add(segment.speaker);
            }
        });

        return {
            totalSegments: this.currentTranscript.length,
            totalDuration: totalDuration,
            totalWords: totalWords,
            speakersCount: speakers.size,
            speakers: Array.from(speakers)
        };
    }

    // Очистка транскрипта
    clearTranscript() {
        this.currentTranscript = null;
        this.currentHighlightedSegment = null;
        
        const transcriptContent = document.getElementById('transcriptContent');
        if (transcriptContent) {
            transcriptContent.innerHTML = '';
        }
    }

    // Получение текущего транскрипта
    getCurrentTranscript() {
        return this.currentTranscript;
    }
}

// Экспорт для использования в других модулях
window.TranscriptManager = TranscriptManager; 
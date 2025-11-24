/**
 * AudioWorklet процессор для real-time захвата аудио
 * 
 * Этот модуль работает в отдельном потоке и обрабатывает аудио данные
 */

class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        
        this.bufferSize = 0;
        this.buffer = [];
        this.sampleRate = 16000; // Целевая частота для WhisperX
        
        // Слушаем сообщения от главного потока
        this.port.onmessage = (event) => {
            if (event.data.command === 'updateConfig') {
                this.bufferSize = event.data.bufferSize;
                this.sampleRate = event.data.sampleRate;
            }
        };
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        if (input && input.length > 0) {
            const inputChannel = input[0]; // Берем первый канал (моно)
            
            // Добавляем данные в буфер
            for (let i = 0; i < inputChannel.length; i++) {
                this.buffer.push(inputChannel[i]);
            }
            
            // Если буфер достиг нужного размера, отправляем данные
            if (this.buffer.length >= this.bufferSize) {
                // Конвертируем float32 в int16 для отправки
                const int16Buffer = new Int16Array(this.buffer.length);
                for (let i = 0; i < this.buffer.length; i++) {
                    // Ограничиваем значения и конвертируем в int16
                    const sample = Math.max(-1, Math.min(1, this.buffer[i]));
                    int16Buffer[i] = sample * 32767;
                }
                
                // Отправляем данные в главный поток
                this.port.postMessage({
                    type: 'audioData',
                    data: int16Buffer,
                    length: int16Buffer.length
                });
                
                // Очищаем буфер
                this.buffer = [];
            }
        }
        
        return true; // Продолжаем обработку
    }
}

registerProcessor('audio-processor', AudioProcessor); 
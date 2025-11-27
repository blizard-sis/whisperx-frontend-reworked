import threading
import whisperx

from ..utils import DependencyValidationError, validate_whisperx_dependencies


class WhisperManager:
    """Менеджер для работы с моделью Whisper"""
    
    def __init__(self, device: str):
        self.model = None
        self.is_loaded = False
        self.loading_lock = threading.Lock()
        self.device = device
            
    def load_model(self, model_name: str):
        """Загрузка модели Whisper"""
        with self.loading_lock:

            try:
                validate_whisperx_dependencies()
            except DependencyValidationError as dep_error:
                error_message = str(dep_error)
                raise RuntimeError(f"Не удалось загрузить модель Whisper из-за отсутствующих зависимостей: {error_message}") from dep_error
            
            self.model = whisperx.load_model(
                model_name, 
                self.device, 
                compute_type="float16"
            )
            self.is_loaded = True
    
    def transcribe(self, audio, batch_size: int = 16, language: str = "ru") -> dict:
        """
        Выполнение транскрипции аудио
        
        Args:
            audio: Аудио данные (numpy array)
            batch_size: Размер батча
            language: Язык для транскрипции
        
        Returns:
            Результат транскрипции
        """
        if not self.is_loaded:
            raise RuntimeError("Модель Whisper не загружена. Вызовите load_model() сначала.")
        
        return self.model.transcribe(audio, batch_size=batch_size, language=language)
    
    async def transcribe_chunk(self, audio_data, sample_rate: int = 16000, language: str = "ru") -> str:
        """
        Транскрипция аудио чанка для real-time режима
        
        Args:
            audio_data: Numpy array с аудио данными
            sample_rate: Частота дискретизации
            language: Язык для транскрипции
            
        Returns:
            str: Результат транскрипции
        """
        if not self.is_loaded:
            # Для real-time нужно загрузить базовую модель
            self.load_model(model_name="base")
        
        try:
            # Убеждаемся, что audio_data - это numpy array float32
            import numpy as np
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data, dtype=np.float32)
            elif audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # WhisperX ожидает аудио с частотой 16kHz, нужно ресемплировать если нужно
            if sample_rate != 16000:
                # Простое ресемплирование (в продакшене лучше использовать librosa)
                import scipy.signal
                target_length = int(len(audio_data) * 16000 / sample_rate)
                audio_data = scipy.signal.resample(audio_data, target_length)
            
            # Транскрибируем аудио чанк
            result = self.model.transcribe(audio_data, batch_size=1, language=language)
            
            # Извлекаем текст из результата
            if result and "segments" in result and result["segments"]:
                text_parts = []
                for segment in result["segments"]:
                    if "text" in segment:
                        text_parts.append(segment["text"].strip())
                
                return " ".join(text_parts).strip()
            return ""
            
        except Exception as e:
            print(f"❌ Ошибка транскрипции чанка: {e}")
            return ""
    
    def cleanup(self):
        """Очистка ресурсов модели"""
        if self.model is not None:
            del self.model
            self.model = None
        
        self.is_loaded = False

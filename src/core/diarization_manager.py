import whisperx

class DiarizationManager:
    """Менеджер для работы с моделью диаризации спикеров"""
    
    def __init__(self, device: str):
        """
        Инициализация менеджера диаризации
        
        Args:
            device: Устройство для работы модели (cuda/cpu)
        """
        self.device = device
        self.model = None
        self.is_loaded = False
            
    def load_model(self, hf_token: str):
        """
        Загрузка модели диаризации
        
        Args:
            hf_token: HuggingFace токен для доступа к pyannote.audio
        """
        try:
            self.model = whisperx.diarize.DiarizationPipeline(
                use_auth_token=hf_token, 
                device=self.device
            )
            self.is_loaded = True
            
        except Exception as e:
            self.model = None
            self.is_loaded = False
            raise RuntimeError(f"Не удалось загрузить модель диаризации: {e}") from e
    
    def diarize(self, audio):
        """
        Выполнение диаризации аудио с автоопределением количества спикеров
        
        Args:
            audio: Аудио данные (numpy array)
            
        Returns:
            Tuple: (diarize_segments, speaker_embeddings) - результат диаризации и векторы голосов
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Модель диаризации не загружена. Вызовите load_model() сначала.")
        
        return self.model(audio, return_embeddings=True)
    
    def cleanup(self):
        """Очистка ресурсов модели"""
        if self.model is not None:
            del self.model
            self.model = None
        
        self.is_loaded = False

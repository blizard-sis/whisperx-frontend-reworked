"""
Менеджер для работы с моделью диаризации спикеров (pyannote.audio)
"""
import whisperx
from typing import Optional, Callable


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
        
        print(f"👥 DiarizationManager инициализирован: device={device}")
    
    def load_model(self, hf_token: str, status_callback: Optional[Callable] = None):
        """
        Загрузка модели диаризации
        
        Args:
            hf_token: HuggingFace токен для доступа к pyannote.audio
            status_callback: Callback для обновления статуса
        """
        if self.is_loaded:
            print("✅ Модель диаризации уже загружена")
            return
        
        try:
            if status_callback:
                status_callback("loading_diarize_model", "Загрузка модели диаризации...", 28)
            
            print("🔧 Загрузка модели диаризации...")
            print(f"🔑 HF Token для диаризации: {hf_token[:20]}...{hf_token[-10:] if len(hf_token) > 30 else hf_token}")
            print(f"🔑 Длина токена: {len(hf_token)} символов")
            print(f"🔑 Токен начинается с 'hf_': {hf_token.startswith('hf_')}")
            
            self.model = whisperx.diarize.DiarizationPipeline(
                use_auth_token=hf_token, 
                device=self.device
            )
            
            self.is_loaded = True
            print("✅ Модель диаризации загружена успешно")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели диаризации: {e}")
            self.model = None
            self.is_loaded = False
            raise
    
    def diarize(self, audio):
        """
        Выполнение диаризации аудио
        
        Args:
            audio: Аудио данные (numpy array)
            
        Returns:
            Результат диаризации с метками спикеров
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Модель диаризации не загружена. Вызовите load_model() сначала.")
        
        print("👥 Диаризация спикеров...")
        return self.model(audio)
    
    def cleanup(self):
        """Очистка ресурсов модели"""
        if self.model is not None:
            del self.model
            self.model = None
        
        self.is_loaded = False
        print("🧹 DiarizationManager очищен")

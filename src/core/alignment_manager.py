"""
Менеджер для работы с моделью выравнивания временных меток (WhisperX Alignment)
"""
import whisperx
from typing import Optional, Callable, Tuple, Any


class AlignmentManager:
    """Менеджер для работы с моделью выравнивания временных меток"""
    
    def __init__(self, device: str = "cuda"):
        """
        Инициализация менеджера выравнивания
        
        Args:
            device: Устройство для работы модели (cuda/cpu)
        """
        self.device = device
        self.model = None
        self.metadata = None
        self.is_loaded = False
        
        print(f"📐 AlignmentManager инициализирован: device={device}")
    
    def load_model(self, language: str, status_callback: Optional[Callable] = None):
        """
        Загрузка модели выравнивания
        
        Args:
            language: Код языка для модели выравнивания
            status_callback: Callback для обновления статуса
        """
        if self.is_loaded:
            print("✅ Модель выравнивания уже загружена")
            return
        
        if status_callback:
            status_callback("loading_align_model", "Загрузка модели выравнивания...", 25)
        
        print("🔧 Загрузка модели выравнивания...")
        
        # Попытка загрузить модель выравнивания с обработкой ошибок
        try:
            self.model, self.metadata = whisperx.load_align_model(
                language_code=language, 
                device=self.device
            )
            print(f"✅ Модель выравнивания загружена для языка: {language}")
            self.is_loaded = True
        except Exception as e:
            print(f"⚠️ Не удалось загрузить модель выравнивания для языка '{language}': {e}")
            print("🔧 Попытка загрузить универсальную модель выравнивания...")
            try:
                # Попробуем загрузить для английского языка как fallback
                self.model, self.metadata = whisperx.load_align_model(
                    language_code="en", 
                    device=self.device
                )
                print("✅ Загружена английская модель выравнивания как fallback")
                self.is_loaded = True
            except Exception as e2:
                print(f"❌ Не удалось загрузить модель выравнивания: {e2}")
                print("⚠️ Транскрипция будет выполнена без точного выравнивания временных меток")
                self.model = None
                self.metadata = None
                self.is_loaded = False
    
    def align(self, segments: list, audio, status_callback: Optional[Callable] = None) -> dict:
        """
        Выполнение выравнивания сегментов транскрипции
        
        Args:
            segments: Сегменты транскрипции
            audio: Аудио данные (numpy array)
            status_callback: Callback для обновления статуса
            
        Returns:
            Результат выравнивания с точными временными метками
        """
        if not self.is_loaded or self.model is None or self.metadata is None:
            print("⚠️ Модель выравнивания не загружена, пропускаем выравнивание")
            return {"segments": segments}
        
        if status_callback:
            status_callback("aligning", "Выравнивание текста...", 65)
        
        print("📐 Выравнивание текста...")
        
        result = whisperx.align(
            segments, 
            self.model, 
            self.metadata, 
            audio, 
            self.device
        )
        
        return result
    
    def cleanup(self):
        """Очистка ресурсов модели"""
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.metadata is not None:
            del self.metadata
            self.metadata = None
        
        self.is_loaded = False
        print("🧹 AlignmentManager очищен")

import whisperx

class AlignmentManager:
    """Менеджер для работы с моделью выравнивания временных меток"""
    
    def __init__(self, device: str):
        """
        Инициализация менеджера выравнивания
        
        Args:
            device: Устройство для работы модели (cuda/cpu)
        """
        self.device = device
        self.model = None
        self.metadata = None
        self.is_loaded = False
            
    def load_model(self, language: str):
        """
        Загрузка модели выравнивания
        
        Args:
            language: Код языка для модели выравнивания
        """
        
        # Попытка загрузить модель выравнивания с обработкой ошибок
        try:
            self.model, self.metadata = whisperx.load_align_model(
                language_code=language, 
                device=self.device
            )
            self.is_loaded = True
        except Exception as e:
            try:
                # Попробуем загрузить для английского языка как fallback
                self.model, self.metadata = whisperx.load_align_model(
                    language_code="en", 
                    device=self.device
                )
                self.is_loaded = True
            except Exception as e2:
                self.model = None
                self.metadata = None
                self.is_loaded = False
                raise RuntimeError(f"Не удалось загрузить модель выравнивания: {e} | Fallback ошибка: {e2}") from e2
    
    def align(self, segments: list, audio) -> dict:
        """
        Выполнение выравнивания сегментов транскрипции
        
        Args:
            segments: Сегменты транскрипции
            audio: Аудио данные (numpy array)
            
        Returns:
            Результат выравнивания с точными временными метками
        """
        if not self.is_loaded:
            raise RuntimeError("Модель выравнивания не загружена.")

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

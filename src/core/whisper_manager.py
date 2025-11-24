"""
Менеджер для работы с моделями WhisperX
"""
import os
import threading
import torch
import json
from typing import Optional, Callable, Dict, Any

import whisperx

from ..models.schemas import TranscriptionConfig
from ..utils import DependencyValidationError, validate_whisperx_dependencies


class WhisperManager:
    """Менеджер для работы с моделями WhisperX"""
    
    def __init__(self):
        self.model = None
        self.align_model = None
        self.align_metadata = None
        self.diarize_model = None
        self.summarization_model = None
        self.summarization_tokenizer = None
        self.models_loaded = False
        self.loading_lock = threading.Lock()
        self.device = self._detect_device()
        self.compute_type = self._detect_compute_type()
        print(f"🔧 Обнаружено устройство: {self.device}, compute_type: {self.compute_type}")
    
    def _detect_device(self) -> str:
        """Определение доступного устройства"""
        if torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def _detect_compute_type(self) -> str:
        """Автоматическое определение compute_type"""
        if self.device == "cuda":
            # Проверяем поддержку float16 на GPU
            try:
                # Пробуем создать тензор float16 на GPU
                test_tensor = torch.tensor([1.0], dtype=torch.float16, device="cuda")
                return "float16"
            except Exception:
                return "float32"
        else:
            # Для CPU используем int8 для лучшей производительности
            return "int8"
    
    def load_models(self, config: TranscriptionConfig, status_callback: Optional[Callable] = None):
        """Загрузка моделей WhisperX в память"""
        with self.loading_lock:
            if self.models_loaded:
                return

            try:
                validate_whisperx_dependencies()
            except DependencyValidationError as dep_error:
                error_message = str(dep_error)
                print(f"❌ Ошибка проверки зависимостей WhisperX: {error_message}")
                if status_callback:
                    status_callback("dependency_error", error_message, 0)
                raise RuntimeError(error_message) from dep_error
            
            # Определяем compute_type
            compute_type = config.compute_type
            if compute_type == "auto":
                compute_type = self.compute_type
                print(f"🔧 Автоматически выбран compute_type: {compute_type}")
            
            if status_callback:
                status_callback("loading_whisper_model", "Загрузка модели Whisper...", 20)
            print(f"🔧 Загрузка модели Whisper: {config.model}")
            self.model = whisperx.load_model(
                config.model, 
                self.device, 
                compute_type=compute_type
            )
            
            if status_callback:
                status_callback("loading_align_model", "Загрузка модели выравнивания...", 25)
            print("🔧 Загрузка модели выравнивания...")
            
            # Попытка загрузить модель выравнивания с обработкой ошибок
            try:
                self.align_model, self.align_metadata = whisperx.load_align_model(
                    language_code=config.language, 
                    device=self.device
                )
            except Exception as e:
                print(f"⚠️ Не удалось загрузить модель выравнивания для языка '{config.language}': {e}")
                print("🔧 Попытка загрузить универсальную модель выравнивания...")
                try:
                    # Попробуем загрузить для английского языка как fallback
                    self.align_model, self.align_metadata = whisperx.load_align_model(
                        language_code="en", 
                        device=self.device
                    )
                    print("✅ Загружена английская модель выравнивания как fallback")
                except Exception as e2:
                    print(f"❌ Не удалось загрузить модель выравнивания: {e2}")
                    print("⚠️ Транскрипция будет выполнена без точного выравнивания временных меток")
                    self.align_model = None
                    self.align_metadata = None
            
            if config.diarize and config.hf_token:
                if status_callback:
                    status_callback("loading_diarize_model", "Загрузка модели диаризации...", 28)
                print("🔧 Загрузка модели диаризации...")
                print(f"🔑 HF Token для диаризации: {config.hf_token[:20]}...{config.hf_token[-10:] if len(config.hf_token) > 30 else config.hf_token}")
                print(f"🔑 Длина токена: {len(config.hf_token)} символов")
                print(f"🔑 Токен начинается с 'hf_': {config.hf_token.startswith('hf_')}")
                self.diarize_model = whisperx.diarize.DiarizationPipeline(
                    use_auth_token=config.hf_token, 
                    device=self.device
                )
            
            self.models_loaded = True
            print("✅ Модели загружены успешно!")
    
    def load_summarization_model(self, model_name: str = None, status_callback: Optional[Callable] = None):
        """Загрузка модели суммаризации"""
        if self.summarization_model is not None:
            print("✅ Модель суммаризации уже загружена")
            return
        
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            if status_callback:
                status_callback("loading_summarization_model", "Загрузка модели суммаризации...", 75)
            
            model_name = model_name or os.getenv('SUMMARIZATION_MODEL', 'Qwen/Qwen2.5-7B-Instruct')
            print(f"🤖 Загрузка модели суммаризации: {model_name}")
            
            # Загружаем токенайзер
            self.summarization_tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            
            # Загружаем модель на доступную GPU
            self.summarization_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto",  # Автоматически выбирает свободную GPU
                trust_remote_code=True
            )
            
            self.summarization_model.eval()
            print(f"✅ Модель суммаризации загружена на устройство: {self.summarization_model.device}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели суммаризации: {e}")
            self.summarization_model = None
            self.summarization_tokenizer = None
            raise
    
    def create_summary(self, transcription_result: dict, status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Создание суммаризации транскрипции
        
        Args:
            transcription_result: Результат транскрипции с сегментами
            status_callback: Callback для обновления статуса
            
        Returns:
            Словарь с суммаризацией
        """
        if self.summarization_model is None:
            self.load_summarization_model(status_callback=status_callback)
        
        try:
            if status_callback:
                status_callback("summarizing", "Создание суммаризации...", 78)
            
            print("📝 Подготовка данных для суммаризации...")
            
            # Извлекаем данные
            segments = transcription_result.get('segments', [])
            speakers_data = {}
            speaker_times = {}
            total_time = 0
            
            for segment in segments:
                speaker = segment.get('speaker', 'UNKNOWN')
                text = segment.get('text', '').strip()
                duration = segment.get('end', 0) - segment.get('start', 0)
                
                if speaker not in speakers_data:
                    speakers_data[speaker] = []
                    speaker_times[speaker] = 0
                
                if text:
                    speakers_data[speaker].append(text)
                
                speaker_times[speaker] += duration
                total_time += duration
            
            # Вычисляем проценты
            speaker_percentages = {}
            for speaker, time in speaker_times.items():
                speaker_percentages[speaker] = round((time / total_time) * 100, 2) if total_time > 0 else 0
            
            total_duration = segments[-1].get('end', 0) / 60 if segments else 0
            
            # Создаём промпт
            prompt = self._create_summarization_prompt(speakers_data, speaker_percentages, total_duration)
            
            if status_callback:
                status_callback("summarizing", "Генерация суммаризации...", 82)
            
            print("🤖 Запуск генерации суммаризации...")
            summary = self._generate_summary(prompt)
            
            print("✅ Суммаризация создана успешно")
            return summary
            
        except Exception as e:
            print(f"❌ Ошибка создания суммаризации: {e}")
            raise
    
    def _create_summarization_prompt(self, speakers_data: Dict, speaker_percentages: Dict, total_duration: float) -> str:
        """Создание промпта для суммаризации"""
        prompt = f"""Проанализируй следующую транскрипцию разговора и создай структурированное саммари.

ИНФОРМАЦИЯ О РАЗГОВОРЕ:
- Общая продолжительность: {total_duration:.1f} минут
- Количество спикеров: {len(speakers_data)}

ДАННЫЕ ПО СПИКЕРАМ:
"""
        
        for speaker, texts in speakers_data.items():
            percentage = speaker_percentages.get(speaker, 0)
            prompt += f"\n--- {speaker} (говорил {percentage}% времени) ---\n"
            prompt += "\n".join(texts[:10])  # Первые 10 фраз
            if len(texts) > 10:
                prompt += f"\n... и еще {len(texts) - 10} фраз"
            prompt += "\n"
        
        prompt += """
ЗАДАЧА:
1. Определи тип разговора (деловая встреча, интервью, лекция и т.д.)
2. Выдели ключевые моменты
3. Проанализируй вклад каждого спикера
4. Создай краткое резюме

Ответь в формате JSON со следующей структурой:
{
  "conversation_type": "тип разговора",
  "key_points": ["пункт 1", "пункт 2", ...],
  "speakers_summary": {
    "SPEAKER_00": "краткое описание вклада",
    ...
  },
  "overall_summary": "общее резюме разговора"
}"""
        
        return prompt
    
    def _generate_summary(self, prompt: str) -> Dict[str, Any]:
        """Генерация суммаризации с помощью LLM"""
        messages = [
            {"role": "system", "content": "Ты эксперт по анализу разговоров. Отвечай только в формате JSON."},
            {"role": "user", "content": prompt}
        ]
        
        # Применяем chat template
        text = self.summarization_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Токенизируем
        model_inputs = self.summarization_tokenizer([text], return_tensors="pt").to(self.summarization_model.device)
        
        # Генерируем
        with torch.no_grad():
            generated_ids = self.summarization_model.generate(
                **model_inputs,
                max_new_tokens=2048,
                temperature=0.3,
                do_sample=True,
                top_p=0.9
            )
        
        # Декодируем
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = self.summarization_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Парсим JSON
        try:
            # Ищем JSON в ответе
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Если JSON не найден, возвращаем как есть
                return {"raw_summary": response}
        except json.JSONDecodeError:
            print(f"⚠️ Не удалось распарсить JSON, возвращаем сырой ответ")
            return {"raw_summary": response}
    
    def transcribe_audio(self, audio_path: str, config: TranscriptionConfig, status_callback: Optional[Callable] = None) -> dict:
        """
        Выполнение транскрипции аудио
        
        Args:
            audio_path: Путь к аудио файлу
            config: Конфигурация транскрипции
            status_callback: Callback для обновления статуса
        
        Returns:
            Результат транскрипции
        """
        if not self.models_loaded:
            self.load_models(config, status_callback)
        
        # Загружаем аудио
        if status_callback:
            status_callback("loading_audio", "Загрузка аудио файла...", 32)
        print(f"🎵 Загрузка аудио файла: {audio_path}")
        audio = whisperx.load_audio(audio_path)
        
        # Транскрипция
        if status_callback:
            status_callback("transcribing", "Выполнение транскрипции...", 45)
        print(f"🎯 Выполнение транскрипции (язык: {config.language})...")
        result = self.model.transcribe(audio, batch_size=config.batch_size, language=config.language)
        
        # Выравнивание
        if self.align_model and self.align_metadata:
            if status_callback:
                status_callback("aligning", "Выравнивание текста...", 65)
            print("📐 Выравнивание текста...")
            result = whisperx.align(
                result["segments"], 
                self.align_model, 
                self.align_metadata, 
                audio, 
                self.device
            )
        
        # Диаризация (если включена)
        if config.diarize and self.diarize_model:
            if status_callback:
                status_callback("diarizing", "Диаризация спикеров...", 72)
            print("👥 Диаризация спикеров...")
            diarize_segments = self.diarize_model(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)
        
        return result
    
    async def transcribe_audio_chunk(self, audio_data, sample_rate: int = 16000, language: str = "ru") -> str:
        """
        Транскрипция аудио чанка для real-time режима
        
        Args:
            audio_data: Numpy array с аудио данными
            sample_rate: Частота дискретизации
            language: Язык для транскрипции
            
        Returns:
            str: Результат транскрипции
        """
        if not self.models_loaded:
            # Для real-time нужно загрузить базовую конфигурацию
            from ..models.schemas import TranscriptionConfig
            basic_config = TranscriptionConfig(
                model="base",
                language=language,
                compute_type="auto",
                batch_size=16,
                diarize=False,
                hf_token=""
            )
            self.load_models(basic_config)
        
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
            result = self.model.transcribe(audio_data, batch_size=1)
            
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
    
    @property
    def is_loaded(self) -> bool:
        """Проверка загружены ли модели"""
        return self.models_loaded 
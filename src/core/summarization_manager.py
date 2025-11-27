"""
Менеджер для работы с моделью суммаризации (vLLM)
"""
import os
import json
import torch
from typing import Optional, Callable, Dict, Any

from transformers import AutoTokenizer, AutoModelForCausalLM


class SummarizationManager:
    """Менеджер для работы с моделью суммаризации"""
    
    def __init__(self, device: str):
        """
        Инициализация менеджера суммаризации
        
        Args:
            device: Устройство для работы модели (cuda/cpu)
        """
        self.device = device
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
        print(f"🤖 SummarizationManager инициализирован: device={device}")
    
    def load_model(self, model_name: str = None, status_callback: Optional[Callable] = None):
        """
        Загрузка модели суммаризации
        
        Args:
            model_name: Название модели (по умолчанию Qwen/Qwen2.5-7B-Instruct)
            status_callback: Callback для обновления статуса
        """
        if self.is_loaded:
            print("✅ Модель суммаризации уже загружена")
            return
        
        try:
            if status_callback:
                status_callback("loading_summarization_model", "Загрузка модели суммаризации...", 75)
            
            if model_name is None:
                from ..config.settings import PROCESSING_CONFIG
                model_name = PROCESSING_CONFIG['summarization_model']
            print(f"🤖 Загрузка модели суммаризации: {model_name}")
            
            # Загружаем токенайзер
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            
            # Всегда используем float16 для максимальной производительности
            dtype = torch.float16
            
            # Загружаем модель на доступную GPU
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                dtype=dtype,
                device_map="auto",
                trust_remote_code=True
            )
            
            self.model.eval()
            self.is_loaded = True
            
            print(f"✅ Модель суммаризации загружена на устройство: {self.model.device}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки модели суммаризации: {e}")
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
            raise
    
    def create_summary(
        self, 
        transcription_result: dict, 
        status_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Создание суммаризации транскрипции
        
        Args:
            transcription_result: Результат транскрипции с сегментами
            status_callback: Callback для обновления статуса
            
        Returns:
            Словарь с суммаризацией
        """
        if not self.is_loaded:
            self.load_model(status_callback=status_callback)
        
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
            prompt = self._create_prompt(speakers_data, speaker_percentages, total_duration)
            
            if status_callback:
                status_callback("summarizing", "Генерация суммаризации...", 82)
            
            print("🤖 Запуск генерации суммаризации...")
            summary = self._generate(prompt)
            
            print("✅ Суммаризация создана успешно")
            return summary
            
        except Exception as e:
            print(f"❌ Ошибка создания суммаризации: {e}")
            raise
    
    def _create_prompt(
        self, 
        speakers_data: Dict, 
        speaker_percentages: Dict, 
        total_duration: float
    ) -> str:
        """
        Создание промпта для суммаризации
        
        Args:
            speakers_data: Данные по спикерам (тексты)
            speaker_percentages: Процент времени говорения каждого спикера
            total_duration: Общая продолжительность в минутах
            
        Returns:
            Промпт для модели
        """
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
    
    def _generate(self, prompt: str) -> Dict[str, Any]:
        """
        Генерация суммаризации с помощью LLM
        
        Args:
            prompt: Промпт для модели
            
        Returns:
            Словарь с результатом суммаризации
        """
        messages = [
            {"role": "system", "content": "Ты эксперт по анализу разговоров. Отвечай только в формате JSON."},
            {"role": "user", "content": prompt}
        ]
        
        # Применяем chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Токенизируем
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        # Генерируем
        with torch.no_grad():
            generated_ids = self.model.generate(
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
        
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
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
    
    def cleanup(self):
        """Очистка ресурсов модели"""
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        self.is_loaded = False
        
        # Очищаем кеш GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print("🧹 SummarizationManager очищен")

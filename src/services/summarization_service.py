"""
Сервис для суммаризации транскрипций
"""
import json
import requests
from typing import Dict, Any, Optional
from ..config.settings import SUMMARIZATION_CONFIG
import logging

logger = logging.getLogger(__name__)

class SummarizationService:
    """Сервис для создания суммаризации транскрипций"""
    
    def __init__(self):
        self.config = SUMMARIZATION_CONFIG
        
    async def create_summary(self, transcription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает суммаризацию на основе данных транскрипции
        
        Args:
            transcription_data: Данные транскрипции с сегментами
            
        Returns:
            Dict с результатом суммаризации
        """
        try:
            logger.info("Начало создания суммаризации")
            
            # Извлекаем данные по спикерам
            speakers_data = self._extract_speaker_data(transcription_data)
            speaker_percentages = self._calculate_speaking_time(transcription_data)
            total_duration = self._calculate_total_duration(transcription_data)
            
            logger.info(f"Найдено спикеров: {len(speakers_data)}")
            logger.info(f"Общая продолжительность: {total_duration:.1f} минут")
            
            # Создаем промпт
            prompt = self._create_summarization_prompt(speakers_data, speaker_percentages, total_duration)
            logger.info(f"Размер промпта: {len(prompt)} символов")
            
            # Отправляем запрос к LLM API
            summary = await self._call_llm_api(prompt)
            
            logger.info("Суммаризация создана успешно")
            return summary
            
        except Exception as e:
            logger.error(f"Ошибка создания суммаризации: {e}")
            raise
    
    def _extract_speaker_data(self, transcription_data: Dict[str, Any]) -> Dict[str, list]:
        """Извлекает данные по спикерам из транскрипции"""
        speakers_data = {}
        
        segments = transcription_data.get('segments', [])
        for segment in segments:
            speaker = segment.get('speaker', 'UNKNOWN')
            text = segment.get('text', '').strip()
            
            if speaker not in speakers_data:
                speakers_data[speaker] = []
            
            if text:
                speakers_data[speaker].append(text)
        
        return speakers_data
    
    def _calculate_speaking_time(self, transcription_data: Dict[str, Any]) -> Dict[str, float]:
        """Вычисляет время говорения каждого спикера в процентах"""
        speaker_times = {}
        total_time = 0
        
        segments = transcription_data.get('segments', [])
        for segment in segments:
            speaker = segment.get('speaker', 'UNKNOWN')
            duration = (segment.get('end', 0) - segment.get('start', 0))
            
            if speaker not in speaker_times:
                speaker_times[speaker] = 0
            
            speaker_times[speaker] += duration
            total_time += duration
        
        # Конвертируем в проценты
        speaker_percentages = {}
        for speaker, time in speaker_times.items():
            speaker_percentages[speaker] = round((time / total_time) * 100, 2) if total_time > 0 else 0
        
        return speaker_percentages
    
    def _calculate_total_duration(self, transcription_data: Dict[str, Any]) -> float:
        """Вычисляет общую продолжительность в минутах"""
        segments = transcription_data.get('segments', [])
        if segments:
            last_segment = segments[-1]
            return (last_segment.get('end', 0)) / 60  # в минутах
        return 0
    
    def _create_summarization_prompt(self, speakers_data: Dict[str, list], 
                                   speaker_percentages: Dict[str, float], 
                                   total_duration: float) -> str:
        """Создает промпт для суммаризации"""
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
1. Выбери оптимальную стратегию анализа (деловая встреча, интервью, лекция, дискуссия и т.д.)
2. Выдели ключевые моменты с временными метками
3. Проанализируй вклад каждого спикера
4. Создай финальное саммари с выводами

Ответь в формате JSON согласно схеме."""
        
        return prompt
    
    async def _call_llm_api(self, prompt: str) -> Dict[str, Any]:
        """Отправляет запрос к LLM API"""
        
        # JSON схема для structured output
        summarization_schema = {
            "type": "object",
            "properties": {
                "strategy_analysis": {
                    "type": "object",
                    "properties": {
                        "chosen_strategy": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "alternative_strategies": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["chosen_strategy", "reasoning", "alternative_strategies"]
                },
                "key_milestones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "speaker": {"type": "string"},
                            "milestone": {"type": "string"},
                            "importance": {"type": "string", "enum": ["high", "medium", "low"]}
                        },
                        "required": ["timestamp", "speaker", "milestone", "importance"]
                    }
                },
                "speakers_analysis": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "main_topics": {"type": "array", "items": {"type": "string"}},
                            "speaking_time_percentage": {"type": "number"},
                            "key_points": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["main_topics", "speaking_time_percentage", "key_points"]
                    }
                },
                "final_summary": {
                    "type": "object",
                    "properties": {
                        "overall_theme": {"type": "string"},
                        "main_discussion_points": {"type": "array", "items": {"type": "string"}},
                        "conclusions": {"type": "array", "items": {"type": "string"}},
                        "action_items": {"type": "array", "items": {"type": "string"}},
                        "duration_minutes": {"type": "number"}
                    },
                    "required": ["overall_theme", "main_discussion_points", "conclusions", "action_items", "duration_minutes"]
                }
            },
            "required": ["strategy_analysis", "key_milestones", "speakers_analysis", "final_summary"]
        }
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - эксперт по анализу и суммаризации разговоров. Твоя задача - создать структурированное и информативное саммари транскрипции, выбрав оптимальную стратегию анализа и выделив ключевые моменты."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": self.config['model'],
            "max_tokens": self.config['max_tokens'],
            "temperature": self.config['temperature'],
            "guided_json": json.dumps(summarization_schema),
            "guided_decoding_backend": "xgrammar",
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "top_p": 0.9,
            "n": 1,
            "stream": False
        }
        
        logger.info(f"Отправка запроса к LLM API: {self.config['api_url']}")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config["api_key"]}'
        }
        
        response = requests.post(
            self.config['api_url'],
            headers=headers,
            json=request_data,
            timeout=120  # 2 минуты таймаут
        )
        
        logger.info(f"Ответ от LLM API получен, статус: {response.status_code}")
        
        if not response.ok:
            error_text = response.text
            logger.error(f"Ошибка LLM API: {response.status_code} - {error_text}")
            raise Exception(f"API error: {response.status_code} - {error_text}")
        
        result = response.json()
        
        if not result.get('choices') or not result['choices'][0].get('message'):
            logger.error(f"Неожиданная структура ответа: {result}")
            raise Exception('Неверная структура ответа от LLM API')
        
        summary_json = json.loads(result['choices'][0]['message']['content'])
        logger.info("Суммаризация успешно распарсена")
        
        return summary_json 
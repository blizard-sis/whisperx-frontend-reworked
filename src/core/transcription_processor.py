import json
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import traceback

from ..models.schemas import TranscriptionConfig
from ..services.subtitle_generator import SubtitleGenerator
from ..services.database_service import DatabaseService
from ..core.whisper_manager import WhisperManager
from ..core.alignment_manager import AlignmentManager
from ..core.diarization_manager import DiarizationManager
from ..core.summarization_manager import SummarizationManager
from ..config.settings import UPLOADS_DIR, TEMP_DIR, TRANSCRIPTS_DIR, PROCESSING_CONFIG
import whisperx
import torch


class TranscriptionProcessor:
    """Основной процессор транскрипции"""
    
    def __init__(self):
        # Определяем устройство для всех моделей (compute_type=float16 захардкожен)
        self.device = self._detect_device()
        
        print(f"🖥️ TranscriptionProcessor: device={self.device}")
        
        # Инициализируем все менеджеры с общими параметрами
        self.whisper_manager = WhisperManager(device=self.device)
        self.alignment_manager = AlignmentManager(device=self.device)
        self.diarization_manager = DiarizationManager(device=self.device)
        self.summarization_manager = SummarizationManager(device=self.device)
        
        # Сервисы
        self.subtitle_generator = SubtitleGenerator()
        self.db_service = DatabaseService()
        self.executor = ThreadPoolExecutor(max_workers=PROCESSING_CONFIG['max_workers'])
        self.task_statuses = {}  # Статусы задач в памяти
        
        print("🎬 TranscriptionProcessor инициализирован со всеми менеджерами")
    
    def _detect_device(self) -> str:
        """Определение доступного устройства для всех моделей"""
        if torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def _detect_compute_type(self) -> str:
        """Автоматическое определение compute_type для максимального качества"""
        compute_type = PROCESSING_CONFIG.get('default_compute_type')
        if not compute_type:
            if self.device == "cuda":
                # Для максимального качества всегда пытаемся использовать float32 на GPU
                # float32 даёт лучшую точность, чем float16
                try:
                    # Проверяем доступность GPU памяти
                    import torch.cuda
                    gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    print(f"🖥️ Доступно GPU памяти: {gpu_mem_gb:.2f} GB")
                    
                    # Если есть хотя бы 8GB - используем float32 для максимального качества
                    if gpu_mem_gb >= 8:
                        print("✅ Используем float32 для максимального качества")
                        return "float32"
                    else:
                        # Для карт с меньшей памятью пробуем float16
                        print("⚠️ Мало GPU памяти, используем float16")
                        return "float16"
                except Exception as e:
                    print(f"⚠️ Ошибка определения GPU памяти: {e}, используем int8")
                    return "int8"
            else:
                # Для CPU используем int8 для производительности
                return "int8"
        else:
            return compute_type
    
    def update_task_status(self, task_id: str, status: str, progress: str = None, error: str = None, progress_percent: int = None):
        """Обновление статуса задачи"""
        self.task_statuses[task_id] = {
            "status": status,
            "progress": progress,
            "progress_percent": progress_percent,
            "error": error,
            "updated_at": datetime.now().isoformat()
        }
        print(f"📊 Статус {task_id}: {status} ({progress_percent}%) - {progress}")
    
    def get_task_status(self, task_id: str) -> Dict:
        """Получение статуса задачи"""
        return self.task_statuses.get(task_id, {})
    
    def extract_audio_from_video(self, video_path: Path, audio_path: Path) -> bool:
        """Извлечение аудио из видео файла"""
        try:
            cmd = [
                'ffmpeg', '-i', str(video_path), 
                '-vn', '-acodec', 'pcm_s16le', 
                '-ar', '16000', '-ac', '1', 
                str(audio_path), '-y'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Ошибка извлечения аудио: {e}")
            return False
    
    def process_transcription_sync(
        self,
        task_id: str,
        file_path: Path,
        config: TranscriptionConfig,
        original_filename: str
    ):
        """Процедура разбора и обработки входных данных для транскрипции"""
        try:
            # Этап 1: Подготовка (0-10%)
            self.update_task_status(task_id, "preparing", "Подготовка к обработке...", progress_percent=5)
            
            # Определяем, нужно ли извлекать аудио
            file_extension = file_path.suffix.lower().lstrip('.')
            video_formats = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', '3gp', 'mts']
            
            if file_extension in video_formats:
                # Этап 2: Извлечение аудио (10-20%)
                self.update_task_status(task_id, "extracting_audio", "Извлечение аудио из видео...", progress_percent=15)
                audio_path = TEMP_DIR / f"{task_id}_audio.wav"
                if not self.extract_audio_from_video(file_path, audio_path):
                    error_msg = "Ошибка извлечения аудио из видео"
                    self.save_error_result(task_id, error_msg, original_filename)
                    self.update_task_status(task_id, "failed", error=error_msg, progress_percent=0)
                    return
                processing_file = audio_path
            else:
                processing_file = file_path
            
            # Этап 3: Загрузка моделей (20-30%)
            self.update_task_status(task_id, "loading_models", "Загрузка моделей...", progress_percent=22)
            
            # Создаем callback для обновления статуса
            def status_callback(status, message, percent):
                self.update_task_status(task_id, status, message, progress_percent=percent)
            
            # Загружаем Whisper
            if not self.whisper_manager.is_loaded:
                self.whisper_manager.load_model(
                    model_name=config.model,
                    status_callback=status_callback
                )
            
            # Загружаем Alignment
            if not self.alignment_manager.is_loaded:
                self.alignment_manager.load_model(
                    language=config.language,
                    status_callback=status_callback
                )
            
            # Загружаем Diarization
            if config.hf_token and not self.diarization_manager.is_loaded:
                self.diarization_manager.load_model(
                    hf_token=config.hf_token,
                    status_callback=status_callback
                )
            
            # Этап 4: Загрузка аудио (30-35%)
            self.update_task_status(task_id, "loading_audio", "Загрузка аудио файла...", progress_percent=32)
            print(f"🎵 Загрузка аудио файла: {processing_file}")
            audio = whisperx.load_audio(str(processing_file))
            
            # Этап 5: Транскрипция (35-60%)
            result = self.whisper_manager.transcribe(
                audio=audio,
                batch_size=config.batch_size,
                language=config.language,
                status_callback=status_callback
            )
            
            # Этап 6: Выравнивание (60-70%)
            if self.alignment_manager.is_loaded:
                result = self.alignment_manager.align(
                    segments=result["segments"],
                    audio=audio,
                    status_callback=status_callback
                )
            
            # Этап 7: Диаризация (70-75%)
            if config.diarize and self.diarization_manager.is_loaded:
                self.update_task_status(task_id, "diarizing", "Диаризация спикеров...", progress_percent=72)
                
                # Получаем сегменты диаризации и эмбеддинги голосов
                diarize_segments, speaker_embeddings = self.diarization_manager.diarize(audio)
                
                # Назначаем спикеров с fill_nearest=True для максимального покрытия
                result = whisperx.assign_word_speakers(
                    diarize_segments, 
                    result,
                    speaker_embeddings=speaker_embeddings,
                    fill_nearest=True  # Назначать ближайшего спикера даже без точного перекрытия
                )
            
            # Добавляем метаданные
            result["created_at"] = datetime.now().isoformat()
            result["task_id"] = task_id
            result["original_filename"] = original_filename
            result["language"] = config.language
            
            # Этап 8: Суммаризация (75-80%)
            try:
                self.update_task_status(task_id, "summarizing", "Создание суммаризации...", progress_percent=76)
                print(f"🤖 Запуск локальной суммаризации для {task_id}")
                
                def summarization_callback(status, message, percent):
                    self.update_task_status(task_id, status, message, progress_percent=percent)
                
                summary = self.summarization_manager.create_summary(result, summarization_callback)
                result["summary"] = summary
                print(f"✅ Суммаризация завершена для {task_id}")
                
            except Exception as e:
                print(f"⚠️ Ошибка суммаризации (не критично): {e}")
                print(traceback.format_exc())
                result["summary"] = None
            
            # Этап 9: Генерация файлов (80-90%)
            self.update_task_status(task_id, "generating_files", "Генерация файлов субтитров...", progress_percent=85)
            
            # Этап 10: Сохранение файлов (90-95%)
            self.update_task_status(task_id, "saving_files", "Сохранение файлов транскрипции...", progress_percent=92)
            self.save_transcription_result(task_id, result, original_filename)

            # Этап 11: Очистка (95-100%)
            self.update_task_status(task_id, "cleaning_up", "Очистка временных файлов...", progress_percent=97)

            # Очищаем временные файлы
            if processing_file != file_path and processing_file.exists():
                processing_file.unlink()

            # Завершение (100%)
            self.update_task_status(task_id, "completed", "Транскрипция завершена, файлы сохранены локально", progress_percent=100)
            print(f"✅ Транскрипция завершена для {task_id}")
            
        except Exception as e:
            error_msg = f"Ошибка обработки: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            self.save_error_result(task_id, error_msg, original_filename)
            self.update_task_status(task_id, "failed", error=error_msg, progress_percent=0)
    
    async def process_transcription(
        self,
        task_id: str,
        file_path: Path,
        config: TranscriptionConfig,
        original_filename: str
    ):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor, 
            self.process_transcription_sync, 
            task_id, 
            file_path,
            config,
            original_filename
        )

    def save_transcription_result(self, task_id: str, result: Dict[str, Any], filename: str):
        """Сохранение результата транскрипции и локальных файлов."""

        # Генерируем файлы субтитров
        self.update_task_status(task_id, "generating_files", "Генерация файлов субтитров...", progress_percent=80)
        segments = result.get("segments", [])
        subtitle_files = self.subtitle_generator.generate_all_formats(
            segments, task_id, filename, temp=False
        )

        # Фиксируем пути к созданным файлам
        local_files = {fmt: str(Path(path)) for fmt, path in subtitle_files.items()}

        # Сохраняем оригинальный файл
        original_files = list(UPLOADS_DIR.glob(f"{task_id}_*"))
        original_file_path = str(original_files[0]) if original_files else None

        # Создаем данные для базы данных (без сегментов для экономии места)
        self.update_task_status(task_id, "saving_files", "Сохранение данных в базу...", progress_percent=92)

        # Сохраняем полный JSON локально
        full_transcription_data = {
            "id": task_id,
            "filename": filename,
            "status": "completed",
            "created_at": result.get("created_at"),
            "completed_at": datetime.now().isoformat(),
            "segments": segments,
            "language": result.get("language"),
            "summary": result.get("summary")  # Добавляем суммаризацию
        }
        
        print(f"💾 Сохранение суммаризации в JSON: {result.get('summary') is not None}")

        transcript_filename = f"{task_id}_{Path(filename).stem}_full.json"
        transcript_path = TRANSCRIPTS_DIR / transcript_filename
        with open(transcript_path, "w", encoding="utf-8") as json_file:
            json.dump(full_transcription_data, json_file, ensure_ascii=False, indent=2)

        # Сохраняем суммаризацию отдельно, если она есть
        if result.get("summary"):
            summary_filename = f"{task_id}_{Path(filename).stem}_summary.json"
            summary_path = TRANSCRIPTS_DIR / summary_filename
            with open(summary_path, "w", encoding="utf-8") as summary_file:
                json.dump(result["summary"], summary_file, ensure_ascii=False, indent=2)
            local_files["summary"] = str(summary_path)
            print(f"✅ Файл суммаризации создан: {summary_filename}")

        transcription_data = self.db_service.create_completed_record(
            task_id=task_id,
            filename=filename,
            transcript_file=str(transcript_path),
            audio_file=original_file_path,
            subtitle_files=local_files,
            language=result.get("language"),
            segments_count=len(segments),
            duration=result.get("duration", 0),
            summary=result.get("summary")  # Добавляем суммаризацию в БД
        )

        # Сохраняем в JSON базу данных
        self.db_service.add_transcription(transcription_data)

        return transcription_data
    
    def save_error_result(self, task_id: str, error_msg: str, filename: str):
        """Сохранение результата с ошибкой в JSON базу данных"""
        error_data = self.db_service.create_error_record(task_id, filename, error_msg)
        self.db_service.add_transcription(error_data) 
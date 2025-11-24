"""API роуты для транскрипции."""
import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import tempfile
import shutil
import os

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse

from ..models.schemas import (
    TranscriptionStatus,
    TranscriptionResult,
    TranscriptionListItem,
    TranscriptionConfig
)
from ..core.transcription_processor import TranscriptionProcessor
from ..config.settings import UPLOADS_DIR, SUPPORTED_FORMATS, SUMMARIZATION_CONFIG
from ..services.summarization_service import SummarizationService
import logging

logger = logging.getLogger(__name__)

# Создаем роутер
router = APIRouter()

# Глобальный процессор транскрипции
processor = TranscriptionProcessor()

# Сервис суммаризации
summarization_service = SummarizationService()


def build_download_links(task_id: str, db_record: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Формирует ссылки для скачивания файлов и совместимые s3_links."""
    if not task_id:
        return {}, {}
    subtitle_files = db_record.get('subtitle_files') or {}
    transcript_file = db_record.get('transcript_file')
    download_urls: Dict[str, str] = {}
    s3_links: Dict[str, str] = {}

    if transcript_file and Path(transcript_file).exists():
        json_url = f"/api/download/transcript/{task_id}?format=json"
        download_urls['transcript_json'] = json_url
        s3_links['json'] = json_url
        s3_links['full_json_s3_url'] = json_url

    for fmt in ['docx', 'pdf']:
        file_path = subtitle_files.get(fmt)
        if file_path and Path(file_path).exists():
            url = f"/api/download/transcript/{task_id}?format={fmt}"
            download_urls[fmt] = url
            s3_links[fmt] = url

    for fmt in ['srt', 'vtt', 'tsv']:
        file_path = subtitle_files.get(fmt)
        if file_path and Path(file_path).exists():
            url = f"/api/download/subtitle/{task_id}?format={fmt}"
            download_urls[fmt] = url
            s3_links[fmt] = url

    audio_file = db_record.get('audio_file')
    if audio_file and Path(audio_file).exists():
        audio_url = f"/api/download/audio/{task_id}"
        download_urls['audio'] = audio_url
        s3_links['original'] = audio_url

    return download_urls, s3_links


@router.post("/upload", response_model=TranscriptionStatus)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = "large-v3",
    language: str = "ru",
    diarize: bool = False,
    hf_token: Optional[str] = None,
    compute_type: str = "float16",
    batch_size: int = 16
):
    """
    Загрузка файла для транскрипции
    
    Поддерживаемые форматы загрузки:
    - Аудио: mp3, m4a, wav, flac, ogg, wma, aac, opus
    - Видео: mp4, avi, mkv, mov, wmv, flv, webm, 3gp, mts
    
    Доступные форматы экспорта:
    - JSON: полная информация с метаданными
    - SRT: стандартные субтитры для видео
    - VTT: веб-субтитры (WebVTT)
    - TSV: табличный формат для анализа
    - DOCX: документ Microsoft Word
    - PDF: документ PDF с форматированием
    
    Процесс обработки:
    1. Загрузка и транскрипция файла
    2. Создание файлов во всех форматах
    3. Сохранение результатов локально
    4. Предоставление ссылок для скачивания локальных файлов
    """
    # Проверяем формат файла
    file_extension = Path(file.filename).suffix.lower().lstrip('.')
    if file_extension not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"Неподдерживаемый формат файла. Поддерживаются: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Генерируем уникальный ID
    task_id = str(uuid.uuid4())
    
    # Сохраняем файл
    file_path = UPLOADS_DIR / f"{task_id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {str(e)}")
    
    # Если HF токен не передан в запросе, берем из переменных окружения
    if hf_token is None and diarize:
        hf_token = os.getenv('HF_TOKEN')
        print(f"🔑 Получен HF_TOKEN из переменных окружения: {hf_token[:20] if hf_token else 'None'}...")
    
    # Создаем конфигурацию
    config = TranscriptionConfig(
        model=model,
        language=language,
        diarize=diarize,
        hf_token=hf_token,
        compute_type=compute_type,
        batch_size=batch_size
    )
    
    # Инициализируем статус задачи
    processor.update_task_status(task_id, "pending", "Задача добавлена в очередь")
    
    # Запускаем обработку в фоне
    background_tasks.add_task(
        processor.process_transcription,
        task_id,
        file_path,
        config,
        file.filename
    )
    
    return TranscriptionStatus(
        id=task_id,
        status="pending",
        filename=file.filename,
        created_at=datetime.now().isoformat(),
        progress="Задача добавлена в очередь"
    )


@router.get("/status/{task_id}", response_model=TranscriptionResult)
async def get_transcription_status(
    task_id: str
):
    """Получение статуса и результата транскрипции по ID"""
    
    # Проверяем актуальный статус из памяти
    current_status = processor.get_task_status(task_id)
    
    # Проверяем в базе данных
    db_record = processor.db_service.get_transcription(task_id)
    
    if db_record:
        transcript_file = db_record.get('transcript_file')
        segments = []
        if transcript_file and Path(transcript_file).exists():
            try:
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    full_data = json.load(f)
                    segments = full_data.get('segments', [])
            except Exception as e:
                print(f"⚠️ Не удалось загрузить сегменты из {transcript_file}: {e}")

        download_urls, s3_links = build_download_links(task_id, db_record)

        return TranscriptionResult(
            id=db_record['id'],
            filename=db_record['filename'],
            status=db_record['status'],
            created_at=db_record['created_at'],
            completed_at=db_record.get('completed_at'),
            transcript_file=transcript_file,
            audio_file=db_record.get('audio_file'),
            subtitle_files=db_record.get('subtitle_files'),
            s3_links=s3_links or None,
            segments=segments if db_record['status'] == 'completed' else None,
            summary=db_record.get('summary'),  # Добавляем суммаризацию
            error=db_record.get('error'),
            progress=db_record.get('progress'),
            progress_percent=db_record.get('progress_percent')
        )
    
    elif current_status:
        # Задача в процессе
        return TranscriptionResult(
            id=task_id,
            filename="processing...",
            status=current_status.get("status", "unknown"),
            created_at=datetime.now().isoformat(),
            progress=current_status.get("progress"),
            progress_percent=current_status.get("progress_percent"),
            error=current_status.get("error")
        )
    
    else:
        # Проверяем, есть ли файл в uploads (возможно задача только что создана)
        upload_files = list(UPLOADS_DIR.glob(f"{task_id}_*"))
        if upload_files:
            return TranscriptionResult(
                id=task_id,
                filename="pending...",
                status="pending",
                created_at=datetime.now().isoformat(),
                progress="Ожидание обработки"
            )
        else:
            raise HTTPException(status_code=404, detail="Задача не найдена")


@router.get("/transcriptions", response_model=List[TranscriptionListItem])
async def get_all_transcriptions():
    """Получение всех транскрипций из JSON базы данных"""
    transcriptions = processor.db_service.get_all_transcriptions()
    
    results = []
    for data in transcriptions:
        _, s3_links = build_download_links(data.get("id"), data)

        list_item = TranscriptionListItem(
            id=data.get("id"),
            filename=data.get("filename"),
            status=data.get("status"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            transcript_file=data.get("transcript_file"),
            audio_file=data.get("audio_file"),
            subtitle_files=data.get("subtitle_files"),
            s3_links=s3_links or None,
            summary=data.get("summary"),  # Добавляем суммаризацию
            error=data.get("error"),
            progress=data.get("progress"),
            progress_percent=data.get("progress_percent")
        )
        results.append(list_item)
    
    return results


@router.get("/files/{task_id}")
@router.get("/s3-links/{task_id}")
async def get_transcription_files(task_id: str):
    """Получение информации о локально сохраненных файлах транскрипции."""
    db_record = processor.db_service.get_transcription(task_id)

    if not db_record:
        raise HTTPException(status_code=404, detail="Транскрипция не найдена")

    subtitle_files = db_record.get('subtitle_files') or {}
    download_urls, s3_links = build_download_links(task_id, db_record)

    return {
        "task_id": task_id,
        "filename": db_record.get("filename"),
        "created_at": db_record.get("created_at"),
        "completed_at": db_record.get("completed_at"),
        "files": {
            "transcript": db_record.get('transcript_file'),
            "audio": db_record.get('audio_file'),
            "subtitle_files": subtitle_files
        },
        "download_urls": download_urls,
        "s3_links": s3_links
    }


@router.delete("/transcription/{task_id}")
async def delete_transcription(task_id: str):
    """Удаление транскрипции из JSON базы данных"""
    
    # Получаем данные из базы данных
    db_record = processor.db_service.get_transcription(task_id)
    
    deleted_files: List[str] = []

    if not db_record:
        # Проверяем локальные файлы (для совместимости со старыми транскрипциями)
        from ..config.settings import TRANSCRIPTS_DIR

        legacy_files = [
            TRANSCRIPTS_DIR / f"{task_id}.json"
        ]
        legacy_files.extend(UPLOADS_DIR.glob(f"{task_id}_*"))
        for format_type in ['srt', 'vtt', 'tsv', 'docx', 'pdf']:
            legacy_files.extend(TRANSCRIPTS_DIR.glob(f"{task_id}_*.{format_type}"))

        for file_path in legacy_files:
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(str(file_path))

        if not deleted_files:
            raise HTTPException(status_code=404, detail="Транскрипция не найдена")
    else:
        for path_str in [db_record.get('transcript_file'), db_record.get('audio_file')]:
            if path_str:
                file_path = Path(path_str)
                if file_path.exists():
                    file_path.unlink()
                    deleted_files.append(str(file_path))

        for path_str in (db_record.get('subtitle_files') or {}).values():
            if path_str:
                file_path = Path(path_str)
                if file_path.exists():
                    file_path.unlink()
                    deleted_files.append(str(file_path))

        processor.db_service.delete_transcription(task_id)

    # Удаляем из базы данных если запись не найдена, просто пропускаем
    if not db_record:
        processor.db_service.delete_transcription(task_id)

    # Удаляем из статусов
    if task_id in processor.task_statuses:
        del processor.task_statuses[task_id]

    return {
        "message": f"Транскрипция {task_id} удалена",
        "deleted_files": deleted_files
    }


@router.get("/health")
async def health_check():
    """Проверка состояния сервера"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": processor.whisper_manager.is_loaded,
        "active_tasks": len([s for s in processor.task_statuses.values() if s["status"] == "processing"]),
        "supported_formats": list(SUPPORTED_FORMATS)
    }


@router.post("/summarize/{task_id}")
async def create_summarization(
    task_id: str
):
    """
    Создание суммаризации транскрипции
    
    Args:
        task_id: ID задачи транскрипции
        
    Returns:
        dict: Результат суммаризации
    """
    try:
        # Получаем данные транскрипции из базы
        db_record = processor.db_service.get_transcription(task_id)
        
        if not db_record:
            raise HTTPException(status_code=404, detail="Транскрипция не найдена")
        
        if db_record['status'] != 'completed':
            raise HTTPException(status_code=400, detail="Транскрипция еще не завершена")
        
        # Получаем локальный JSON файл
        transcript_file = db_record.get('transcript_file')

        if not transcript_file or not Path(transcript_file).exists():
            raise HTTPException(status_code=404, detail="JSON файл транскрипции не найден")

        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        # Создаем суммаризацию
        summary = await summarization_service.create_summary(transcription_data)
        
        return {
            "task_id": task_id,
            "summary": summary,
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка создания суммаризации для {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания суммаризации: {str(e)}")


@router.get("/config/summarization")
async def get_summarization_config():
    """
    Получение конфигурации суммаризации
    
    Returns:
        dict: Конфигурация суммаризации для клиента
        
    Note:
        Этот endpoint теперь используется только для проверки настроек.
        Сама суммаризация выполняется на бэкенде через /summarize/{task_id}
    """
    return {
        "api_url": SUMMARIZATION_CONFIG['api_url'],
        "model": SUMMARIZATION_CONFIG['model'],
        "max_tokens": SUMMARIZATION_CONFIG['max_tokens'],
        "temperature": SUMMARIZATION_CONFIG['temperature'],
        "has_api_key": bool(SUMMARIZATION_CONFIG['api_key'] and SUMMARIZATION_CONFIG['api_key'] != 'your-api-key-here'),
        "backend_processing": True  # Указываем что обработка происходит на бэкенде
    }


@router.get("/")
async def root():
    """Главная страница API"""
    return {
        "message": "redmadtrancribe x WhisperX API v2.0",
        "description": "API для транскрипции аудио и видео файлов с экспортом в 6 форматов",
        "supported_formats": {
            "input": list(SUPPORTED_FORMATS),
            "output": ["JSON", "SRT", "VTT", "TSV", "DOCX", "PDF"]
        },
        "features": [
            "✅ Транскрипция с WhisperX",
            "✅ Диаризация спикеров (с HuggingFace токеном)",
            "✅ 6 форматов экспорта: JSON, SRT, VTT, TSV, DOCX, PDF",
            "✅ Локальное хранение и управление файлами",
            "✅ Сохранение результатов в JSON базе данных",
            "✅ JSON база данных",
            "✅ Управление через веб-интерфейс"
        ],
        "formats": {
            "JSON": "Структурированные данные с временными метками",
            "SRT": "Субтитры для видео",
            "VTT": "Веб-субтитры",
            "TSV": "Табличные данные",
            "DOCX": "Документ Microsoft Word", 
            "PDF": "Документ PDF с форматированием"
        },
        "endpoints": {
            "POST /upload": "Загрузка и обработка файла",
            "GET /status/{task_id}": "Статус обработки",
            "GET /transcriptions": "Список всех транскрипций",
            "GET /files/{task_id}": "Информация о локальных файлах",
            "GET /download/transcript/{task_id}": "Скачать транскрипт в различных форматах",
            "GET /download/subtitle/{task_id}": "Скачать субтитры",
            "DELETE /transcription/{task_id}": "Удаление транскрипции",
            "GET /health": "Проверка состояния сервера"
        }
    }


@router.get("/download/transcript/{task_id}")
async def download_transcript(
    task_id: str, 
    format_type: str = Query(..., description="Формат файла: json, docx, pdf")
):
    """Скачивание транскрипта в различных форматах"""
    
    # Проверяем корректность формата
    if format_type not in ['json', 'docx', 'pdf']:
        raise HTTPException(status_code=400, detail="Поддерживаемые форматы: json, docx, pdf")
    
    # Получаем данные из базы
    db_record = processor.db_service.get_transcription(task_id)
    
    if not db_record:
        raise HTTPException(status_code=404, detail="Транскрипция не найдена")
    
    if db_record['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Транскрипция еще не завершена")
    
    transcript_file = db_record.get('transcript_file')
    subtitle_files = db_record.get('subtitle_files') or {}

    if format_type == 'json':
        if not transcript_file or not Path(transcript_file).exists():
            raise HTTPException(status_code=404, detail="JSON файл не найден")

        return FileResponse(
            path=transcript_file,
            filename=f"{Path(db_record['filename']).stem}_{task_id}.json",
            media_type='application/json'
        )

    target_path = subtitle_files.get(format_type)

    if not target_path or not Path(target_path).exists():
        if not transcript_file or not Path(transcript_file).exists():
            raise HTTPException(status_code=404, detail="Исходные данные транскрипции не найдены")

        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        segments = transcription_data.get('segments', [])

        if not segments:
            raise HTTPException(status_code=400, detail="Сегменты транскрипции не найдены")

        generator_method = getattr(processor.subtitle_generator, f"generate_{format_type}", None)
        if not generator_method:
            raise HTTPException(status_code=500, detail=f"Генератор для {format_type.upper()} не доступен")

        new_path = generator_method(segments, task_id, db_record['filename'], temp=False)
        if not new_path or not Path(new_path).exists():
            raise HTTPException(status_code=500, detail=f"Не удалось создать {format_type.upper()} файл")

        subtitle_files[format_type] = new_path
        processor.db_service.update_transcription(task_id, {"subtitle_files": subtitle_files})
        target_path = new_path

    media_type = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }.get(format_type, 'application/octet-stream')

    return FileResponse(
        path=target_path,
        filename=f"{Path(db_record['filename']).stem}_{task_id}.{format_type}",
        media_type=media_type
    )


@router.get("/download/subtitle/{task_id}")
async def download_subtitle(
    task_id: str, 
    format_type: str = Query(..., description="Формат субтитров: srt, vtt, tsv")
):
    """Скачивание субтитров в различных форматах"""
    
    # Проверяем корректность формата
    if format_type not in ['srt', 'vtt', 'tsv']:
        raise HTTPException(status_code=400, detail="Поддерживаемые форматы: srt, vtt, tsv")
    
    # Получаем данные из базы
    db_record = processor.db_service.get_transcription(task_id)
    
    if not db_record:
        raise HTTPException(status_code=404, detail="Транскрипция не найдена")
    
    if db_record['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Транскрипция еще не завершена")
    
    subtitle_files = db_record.get('subtitle_files') or {}
    transcript_file = db_record.get('transcript_file')

    target_path = subtitle_files.get(format_type)

    if not target_path or not Path(target_path).exists():
        if not transcript_file or not Path(transcript_file).exists():
            raise HTTPException(status_code=404, detail="Исходные данные транскрипции не найдены")

        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        segments = transcription_data.get('segments', [])

        if not segments:
            raise HTTPException(status_code=400, detail="Сегменты транскрипции не найдены")

        generator_method = getattr(processor.subtitle_generator, f"generate_{format_type}", None)
        if not generator_method:
            raise HTTPException(status_code=500, detail=f"Генератор для {format_type.upper()} не доступен")

        new_path = generator_method(segments, task_id, db_record['filename'], temp=False)
        if not new_path or not Path(new_path).exists():
            raise HTTPException(status_code=500, detail=f"Не удалось создать {format_type.upper()} файл")

        subtitle_files[format_type] = new_path
        processor.db_service.update_transcription(task_id, {"subtitle_files": subtitle_files})
        target_path = new_path

    return FileResponse(
        path=target_path,
        filename=f"{Path(db_record['filename']).stem}_{task_id}.{format_type}",
        media_type='text/plain; charset=utf-8'
    )


@router.get("/download/audio/{task_id}")
async def download_audio(task_id: str):
    """Скачивание оригинального аудио файла"""
    
    # Получаем данные из базы
    db_record = processor.db_service.get_transcription(task_id)
    
    if not db_record:
        raise HTTPException(status_code=404, detail="Транскрипция не найдена")
    
    audio_path = db_record.get('audio_file')

    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail="Аудио файл не найден")

    return FileResponse(
        path=audio_path,
        filename=Path(audio_path).name,
        media_type='application/octet-stream'
    )


@router.get("/download/summary/{task_id}")
async def download_summary(task_id: str):
    """Скачивание файла суммаризации"""
    
    # Получаем данные из базы
    db_record = processor.db_service.get_transcription(task_id)
    
    if not db_record:
        raise HTTPException(status_code=404, detail="Транскрипция не найдена")
    
    subtitle_files = db_record.get('subtitle_files') or {}
    summary_path = subtitle_files.get('summary')

    if not summary_path or not Path(summary_path).exists():
        # Пытаемся найти файл по шаблону, если в БД нет пути
        from ..config.settings import TRANSCRIPTS_DIR
        summary_files = list(TRANSCRIPTS_DIR.glob(f"{task_id}_*_summary.json"))
        if summary_files:
            summary_path = str(summary_files[0])
        else:
            raise HTTPException(status_code=404, detail="Файл суммаризации не найден")

    return FileResponse(
        path=summary_path,
        filename=f"{Path(db_record['filename']).stem}_{task_id}_summary.json",
        media_type='application/json'
    )
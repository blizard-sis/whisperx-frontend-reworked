"""
Сервис для работы с JSON базой данных
"""
import json
import threading
from typing import Dict, List, Optional
from datetime import datetime

from ..config.settings import DATABASE_FILE


class DatabaseService:
    """Сервис для работы с JSON базой данных"""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def load_database(self) -> Dict:
        """Загрузка базы данных из JSON файла"""
        with self.lock:
            if DATABASE_FILE.exists():
                try:
                    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Обеспечиваем структуру базы данных
                        if 'transcriptions' not in data:
                            data['transcriptions'] = {}
                        return data
                except (json.JSONDecodeError, Exception) as e:
                    print(f"⚠️ Ошибка загрузки базы данных: {e}")
                    return {'transcriptions': {}}
            return {'transcriptions': {}}
    
    def save_database(self, db_data: Dict):
        """Сохранение базы данных в JSON файл"""
        with self.lock:
            try:
                # Конвертируем datetime объекты в строки для JSON сериализации
                def convert_datetime(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, dict):
                        return {k: convert_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_datetime(item) for item in obj]
                    return obj
                
                serializable_data = convert_datetime(db_data)
                
                with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"❌ Ошибка сохранения базы данных: {e}")
    
    # Методы для работы с транскрипциями
    def add_transcription(self, transcription_data: Dict):
        """Добавление транскрипции в базу данных"""
        db = self.load_database()
        db['transcriptions'][transcription_data['id']] = transcription_data
        self.save_database(db)
        print(f"✅ Транскрипция {transcription_data['id']} добавлена в базу данных")
    
    def get_transcription(self, task_id: str) -> Optional[Dict]:
        """Получение транскрипции из базы данных"""
        db = self.load_database()
        return db['transcriptions'].get(task_id)
    
    def update_transcription(self, task_id: str, updates: Dict):
        """Обновление транскрипции в базе данных"""
        db = self.load_database()
        if task_id in db['transcriptions']:
            db['transcriptions'][task_id].update(updates)
            self.save_database(db)
            print(f"✅ Транскрипция {task_id} обновлена в базе данных")
    
    def delete_transcription(self, task_id: str) -> bool:
        """Удаление транскрипции из базы данных"""
        db = self.load_database()
        if task_id in db['transcriptions']:
            del db['transcriptions'][task_id]
            self.save_database(db)
            print(f"✅ Транскрипция {task_id} удалена из базы данных")
            return True
        return False
    
    def get_all_transcriptions(self) -> List[Dict]:
        """Получение всех транскрипций из базы данных"""
        db = self.load_database()
        # Сортируем по дате создания (новые сначала)
        transcriptions = list(db['transcriptions'].values())
        transcriptions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return transcriptions
    
    def create_transcription_record(self, task_id: str, filename: str, status: str = "pending", **kwargs) -> Dict:
        """Создание записи транскрипции"""
        record = {
            "id": task_id,
            "filename": filename,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "transcript_file": None,
            "audio_file": None,
            "subtitle_files": {},
            "s3_links": kwargs.pop('s3_links', {}),
            **kwargs
        }
        return record
    
    def create_error_record(self, task_id: str, filename: str, error_msg: str) -> Dict:
        """Создание записи об ошибке"""
        return self.create_transcription_record(
            task_id=task_id,
            filename=filename,
            status="failed",
            error=error_msg
        )

    def create_completed_record(self, task_id: str, filename: str, transcript_file: str = None,
                                audio_file: str = None, subtitle_files: Dict = None, **kwargs) -> Dict:
        """Создание записи о завершенной транскрипции"""
        return self.create_transcription_record(
            task_id=task_id,
            filename=filename,
            status="completed",
            completed_at=datetime.now().isoformat(),
            transcript_file=transcript_file,
            audio_file=audio_file,
            subtitle_files=subtitle_files or {},
            **kwargs
        )
    
    # Методы пользователей и сессий удалены, так как авторизация больше не используется

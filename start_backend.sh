#!/bin/bash
# Скрипт запуска WhisperX Backend

echo "🚀 Запуск WhisperX Backend..."

# Переход в директорию проекта
cd "$(dirname "$0")"

# Активация виртуального окружения
if [ -d "venv" ]; then
    echo "✅ Активация виртуального окружения..."
    source venv/bin/activate
else
    echo "❌ Виртуальное окружение не найдено! Создайте его командой: python -m venv venv"
    exit 1
fi

# Установка LD_LIBRARY_PATH для cuDNN
export LD_LIBRARY_PATH="$(pwd)/venv/lib64/python3.12/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH"
echo "✅ LD_LIBRARY_PATH установлен"

# Загрузка переменных из .env
if [ -f .env ]; then
    echo "✅ Загрузка переменных из .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  Файл .env не найден, используются значения по умолчанию"
fi

# Запуск сервера
echo "🚀 Запуск сервера на порту 8880..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8880

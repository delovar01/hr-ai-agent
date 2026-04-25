#!/usr/bin/env bash
set -e

echo "🚀 Запуск HR AI Agent..."

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Скопируйте .env.example в .env и добавьте GIGACHAT_CREDENTIALS"
    exit 1
fi

# Создание виртуального окружения
echo "📦 Создание виртуального окружения..."
python3 -m venv .venv 2>/dev/null || python -m venv .venv

# Активация виртуального окружения
echo "🔧 Активация окружения..."
source .venv/bin/activate

# Установка зависимостей
echo "📚 Установка зависимостей..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Создание директории для данных
mkdir -p data

# Запуск дашборда
echo "✨ Запуск дашборда..."
echo "🌐 Откройте http://localhost:8501"
streamlit run dashboard/app.py --server.port 8501

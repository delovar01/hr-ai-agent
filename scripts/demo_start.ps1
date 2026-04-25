# scripts/demo_start.ps1
Write-Host "🚀 Запуск HR AI Agent..." -ForegroundColor Green

# Проверка наличия .env файла
if (-not (Test-Path .env)) {
    Write-Host "❌ Файл .env не найден!" -ForegroundColor Red
    Write-Host "📝 Скопируйте .env.example в .env и добавьте GIGACHAT_CREDENTIALS" -ForegroundColor Yellow
    exit 1
}

# Создание виртуального окружения
Write-Host "📦 Создание виртуального окружения..." -ForegroundColor Green
python -m venv .venv

# Активация виртуального окружения
Write-Host "🔧 Активация окружения..." -ForegroundColor Green
.\.venv\Scripts\Activate.ps1

# Установка зависимостей
Write-Host "📚 Установка зависимостей..." -ForegroundColor Green
pip install --upgrade pip
pip install -r requirements.txt

# Создание директории для данных
New-Item -ItemType Directory -Force -Path data

# Запуск дашборда
Write-Host "✨ Запуск дашборда..." -ForegroundColor Green
Write-Host "🌐 Откройте http://localhost:8501" -ForegroundColor Yellow
streamlit run dashboard/app.py --server.port 8501

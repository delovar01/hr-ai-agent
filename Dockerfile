FROM python:3.10-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY src/ ./src/
COPY dashboard/ ./dashboard/
COPY config/ ./config/

# Открываем порт для Streamlit
EXPOSE 8501

# Запускаем дашборд
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

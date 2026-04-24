FROM python:3.10-slim AS builder

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.10-slim

WORKDIR /app

# Копируем зависимости из builder
COPY --from=builder /root/.local /root/.local

# Копируем код
COPY src/ ./src/
COPY dashboard/ ./dashboard/
COPY config/ ./config/

# Добавляем путь к локальным пакетам
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

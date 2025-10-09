# Используем официальный образ Python
FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование файла зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всех файлов проекта
COPY . .

# Создание директории для постоянных данных (будет смонтирована в /data на Amvera)
RUN mkdir -p /data

# Установка переменной окружения для Python (не создавать .pyc файлы)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Запуск бота
CMD ["python", "bot.py"]


#!/bin/bash

# Скрипт быстрого запуска Astro Bot

echo "🚀 Запуск Astro Bot..."

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
if [ ! -f "venv/.deps_installed" ]; then
    echo "📥 Установка зависимостей..."
    pip install -r requirements.txt
    touch venv/.deps_installed
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "📝 Создайте файл .env на основе .env.example"
    echo "   cp .env.example .env"
    echo "   и заполните необходимые переменные"
    exit 1
fi

# Запуск бота
echo "✨ Запуск бота..."
python bot.py


#!/usr/bin/env python
"""
Скрипт для быстрой инициализации курсов в боте
"""

from database import init_db
from utils.admin import AdminPanel

if __name__ == "__main__":
    print("="*60)
    print("🎓 Инициализация курсов Astro Bot")
    print("="*60)
    print()
    
    # Инициализация базы данных
    print("📦 Инициализация базы данных...")
    init_db()
    print("✅ База данных готова")
    print()
    
    # Создание курсов
    print("📚 Создание демо-курсов...")
    AdminPanel.create_sample_courses()
    print()
    
    # Вывод списка курсов
    print("="*60)
    print("📋 Список созданных курсов:")
    print("="*60)
    AdminPanel.list_courses()
    print()
    
    print("="*60)
    print("✨ Готово! Теперь можно запустить бота: python bot.py")
    print("="*60)


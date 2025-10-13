#!/usr/bin/env python
"""
Скрипт для инициализации всех услуг и курсов в боте
"""

from database import init_db
from utils.admin import AdminPanel

if __name__ == "__main__":
    print("="*60)
    print("🎓 Инициализация Astro Bot")
    print("="*60)
    print()
    
    # Инициализация базы данных
    print("📦 Инициализация базы данных...")
    init_db()
    print("✅ База данных готова")
    print()
    
    # Создание всех данных
    print("📚 Создание услуг и курсов...")
    AdminPanel.create_all()
    print()
    
    # Вывод списка
    print("="*60)
    print("📋 СПИСОК КУРСОВ:")
    print("="*60)
    AdminPanel.list_courses()
    print()
    
    print("="*60)
    print("📋 СПИСОК КОНСУЛЬТАЦИЙ:")
    print("="*60)
    AdminPanel.list_consultations()
    print()
    
    print("="*60)
    print("✨ Готово! Теперь можно запустить бота: python bot.py")
    print("="*60)


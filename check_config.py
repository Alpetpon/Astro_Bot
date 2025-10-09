#!/usr/bin/env python
"""
Скрипт для проверки конфигурации бота
"""

import os
from pathlib import Path


def check_env_file():
    """Проверка файла .env"""
    print("🔍 Проверка файла .env...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Файл .env не найден!")
        print("   Создайте его: cp .env.example .env")
        return False
    
    print("✅ Файл .env найден")
    return True


def check_env_variables():
    """Проверка переменных окружения"""
    from dotenv import load_dotenv
    load_dotenv()
    
    print("\n🔍 Проверка переменных окружения...\n")
    
    required_vars = {
        'BOT_TOKEN': 'Токен бота от @BotFather',
        'YOOKASSA_SHOP_ID': 'ID магазина ЮKassa',
        'YOOKASSA_SECRET_KEY': 'Секретный ключ ЮKassa',
        'ADMIN_ID': 'Ваш Telegram ID'
    }
    
    all_ok = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Скрываем часть значения для безопасности
            if len(value) > 10:
                display_value = value[:5] + "..." + value[-5:]
            else:
                display_value = "***"
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: НЕ ЗАДАНА ({description})")
            all_ok = False
    
    return all_ok


def check_database():
    """Проверка базы данных"""
    print("\n🔍 Проверка базы данных...")
    
    try:
        from database import engine, Base
        
        # Проверяем подключение
        with engine.connect() as conn:
            print("✅ Подключение к базе данных успешно")
        
        # Проверяем таблицы
        inspector = engine.dialect.get_inspector(engine.connect())
        tables = inspector.get_table_names()
        
        if tables:
            print(f"✅ Найдено таблиц: {len(tables)}")
            for table in tables:
                print(f"   - {table}")
        else:
            print("⚠️  Таблицы не найдены. Запустите: python setup_courses.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")
        return False


def check_dependencies():
    """Проверка установленных зависимостей"""
    print("\n🔍 Проверка зависимостей...")
    
    required_packages = [
        'aiogram',
        'aiohttp',
        'sqlalchemy',
        'yookassa',
        'apscheduler',
        'python-dotenv'
    ]
    
    all_ok = True
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} не установлен")
            all_ok = False
    
    if not all_ok:
        print("\n💡 Установите зависимости: pip install -r requirements.txt")
    
    return all_ok


def main():
    print("="*60)
    print("🤖 Проверка конфигурации Astro Bot")
    print("="*60)
    print()
    
    checks = []
    
    # Проверка зависимостей
    checks.append(check_dependencies())
    
    # Проверка файла .env
    if check_env_file():
        checks.append(check_env_variables())
    else:
        checks.append(False)
    
    # Проверка базы данных
    if all(checks):
        checks.append(check_database())
    
    print("\n" + "="*60)
    if all(checks):
        print("✅ Все проверки пройдены!")
        print("🚀 Можете запускать бота: python bot.py")
    else:
        print("❌ Найдены проблемы. Исправьте их и повторите проверку.")
    print("="*60)


if __name__ == "__main__":
    main()


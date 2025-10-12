import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация бота"""
    
    # Telegram
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    
    # ЮKassa
    YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
    YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    
    # База данных
    # В продакшене на Amvera используется /data для постоянного хранилища
    # Локально используется текущая директория
    def _get_database_url():
        """Определяет путь к БД в зависимости от окружения"""
        db_url = os.getenv('DATABASE_URL')
        
        if db_url:
            return db_url
        
        # Если директория /data существует (продакшен на Amvera), используем её
        if os.path.exists('/data') and os.path.isdir('/data'):
            return 'sqlite:////data/astro_bot.db'
        
        # Иначе используем локальную директорию
        return 'sqlite:///./astro_bot.db'
    
    DATABASE_URL = _get_database_url()
    
    # Настройки напоминаний
    INACTIVITY_DAYS = 3  # Количество дней без активности для напоминания
    
    # Контакты для консультаций
    CONSULTATION_TELEGRAM = os.getenv('CONSULTATION_TELEGRAM', 'your_username')  # Username без @
    
    # Ссылки на продукты
    GUIDE_RELATIONSHIPS_FILE = os.getenv('GUIDE_RELATIONSHIPS_FILE', '')  # URL или file_id гайда по отношениям
    
    # Соц. сети
    INSTAGRAM_URL = os.getenv('INSTAGRAM_URL', 'https://instagram.com/your_profile')
    YOUTUBE_URL = os.getenv('YOUTUBE_URL', 'https://youtube.com/@your_channel')
    VK_URL = os.getenv('VK_URL', 'https://vk.com/your_profile')
    TELEGRAM_CHANNEL_URL = os.getenv('TELEGRAM_CHANNEL_URL', 'https://t.me/your_channel')
    DZEN_URL = os.getenv('DZEN_URL', 'https://dzen.ru/your_profile')
    
    # Тексты
    WELCOME_TEXT = """
👋 Добро пожаловать в мир астропсихологии!

Я помогу вам:
🌟 Узнать больше о курсах и обучении
📚 Получить доступ к материалам
💫 Отслеживать свой прогресс

Нажмите «Перейти в меню» для продолжения
"""
    
    ABOUT_ME_TEXT = """
👤 **Обо мне**

Профессиональный астролог и психолог с опытом более X лет.

Помогаю людям:
• Познать себя через призму астрологии
• Улучшить отношения
• Найти свое призвание
• Понять жизненные циклы

Моя экспертиза основана на синтезе классической астрологии и современной психологии.
"""
    
    GUIDE_RELATIONSHIPS_TEXT = """
💕 **Гайд по отношениям**

Краткий практический гайд, который поможет вам:
• Понять совместимость партнеров
• Выявить зоны роста в отношениях
• Научиться гармонично взаимодействовать

Формат: PDF-гайд с практическими упражнениями

Цена: 990 ₽
"""


config = Config()


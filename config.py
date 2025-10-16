import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


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
            logger.info(f"Using DATABASE_URL from environment: {db_url}")
            return db_url
        
        # Проверяем переменную окружения для продакшена
        use_persistent = os.getenv('USE_PERSISTENT_STORAGE', 'false').lower() == 'true'
        
        # Пытаемся создать директорию /data если её нет
        data_dir = '/data'
        try:
            if not os.path.exists(data_dir):
                os.makedirs(data_dir, exist_ok=True)
                logger.info(f"Created directory: {data_dir}")
        except Exception as e:
            logger.warning(f"Cannot create {data_dir}: {e}")
        
        # Если директория /data доступна или явно указано использовать persistent storage
        if use_persistent or (os.path.exists(data_dir) and os.path.isdir(data_dir) and os.access(data_dir, os.W_OK)):
            db_path = 'sqlite:////data/astro_bot.db'
            logger.info(f"Using persistent storage: {db_path}")
            return db_path
        
        # Иначе используем локальную директорию
        db_path = 'sqlite:///./astro_bot.db'
        logger.info(f"Using local storage: {db_path}")
        return db_path
    
    DATABASE_URL = _get_database_url()
    
    # Настройки напоминаний
    INACTIVITY_DAYS = 3  # Количество дней без активности для напоминания
    
    # Контакты для консультаций
    CONSULTATION_TELEGRAM = os.getenv('CONSULTATION_TELEGRAM', 'Katrin_fucco')  # Username без @
    
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
    

config = Config()


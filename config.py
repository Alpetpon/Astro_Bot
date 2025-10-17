import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Конфигурация бота"""
    
    # Telegram
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Поддержка нескольких администраторов
    # Можно указать один ID или несколько через запятую
    @staticmethod
    def _parse_admin_ids():
        """Парсинг ADMIN_ID из .env (поддержка нескольких ID через запятую)"""
        admin_str = os.getenv('ADMIN_ID', '0')
        try:
            # Если несколько ID через запятую
            if ',' in admin_str:
                return [int(id.strip()) for id in admin_str.split(',') if id.strip()]
            # Если один ID
            return [int(admin_str)]
        except ValueError:
            logger.error(f"Invalid ADMIN_ID format: {admin_str}")
            return [0]
    
    ADMIN_IDS = _parse_admin_ids()  # Список всех админов
    ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0  # Основной админ (для обратной совместимости)
    
    # ЮKassa
    YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
    YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    
    # База данных MongoDB
    @staticmethod
    def _get_mongodb_url():
        """Получение URL подключения к MongoDB"""
        mongodb_url = os.getenv('MONGODB_URL')
        
        if mongodb_url:
            logger.info("Using MONGODB_URL from environment")
            return mongodb_url
        
        # Локальная MongoDB по умолчанию
        default_url = 'mongodb://localhost:27017'
        logger.info(f"Using default MongoDB URL: {default_url}")
        return default_url
    
    MONGODB_URL = _get_mongodb_url()
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'astro_bot')
    
    # Контакты для консультаций
    CONSULTATION_TELEGRAM = 'Katrin_fucco'  # Username без @
    
    # Соц. сети (можно изменить прямо в коде)
    INSTAGRAM_URL = 'https://instagram.com/your_profile'
    YOUTUBE_URL = 'https://youtube.com/@your_channel'
    VK_URL = 'https://vk.com/your_profile'
    TELEGRAM_CHANNEL_URL = 'https://t.me/your_channel'
    DZEN_URL = 'https://dzen.ru/your_profile'
    
    # Видео (File ID можно указать здесь или загрузить через админ-панель)
    # Значения из админ-панели имеют приоритет над этими
    WELCOME_VIDEO_FILE_ID = ''  # File ID приветственного видео
    ABOUT_ME_VIDEO_FILE_ID = ''  # File ID видео-интервью "Обо мне"
    
    # Тексты
    WELCOME_TEXT = """
👋 Добро пожаловать в мир астропсихологии!

Я помогу вам:
🌟 Узнать больше о курсах и обучении
📚 Получить доступ к материалам
💫 Отслеживать свой прогресс

"""
    
    ABOUT_ME_TEXT = """
👤 **Обо мне**

Профессиональный астролог и психолог с опытом более 10 лет.

Помогаю людям:
• Познать себя через призму астрологии
• Улучшить отношения
• Найти свое призвание
• Понять жизненные циклы

Моя экспертиза основана на синтезе классической астрологии и современной психологии.
"""
    

config = Config()


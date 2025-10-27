import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Конфигурация бота"""
    
    # Telegram - основной бот (воронка продаж)
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Telegram - учебный бот (обучение)
    LEARNING_BOT_TOKEN = os.getenv('LEARNING_BOT_TOKEN')
    LEARNING_BOT_USERNAME = os.getenv('LEARNING_BOT_USERNAME', 'your_learning_bot')  # Username без @
    
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
    
    # Telegram канал для платной подписки
    SUBSCRIPTION_CHANNEL_ID = os.getenv('SUBSCRIPTION_CHANNEL_ID', '')  # Например: -1003244100380
    SUBSCRIPTION_PRICE = float(os.getenv('SUBSCRIPTION_PRICE', '990.00'))
    SUBSCRIPTION_DAYS = int(os.getenv('SUBSCRIPTION_DAYS', '30'))
    SUBSCRIPTION_CURRENCY = os.getenv('SUBSCRIPTION_CURRENCY', 'RUB')
    
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
    INSTAGRAM_URL = 'https://www.instagram.com/ohuevshaya_i?igsh=aTF0YnltanIzYm5z'
    YOUTUBE_URL = 'https://youtube.com/@katrin_f?si=y3piuaqhKwAX10OR'
    VK_URL = 'https://sponsr.ru/katrin_fucco'
    TELEGRAM_CHANNEL_URL = 'https://t.me/astrotaroKatrinF'
    DZEN_URL = 'https://dzen.ru/katrin_fucco'
    
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
    
    MAIN_MENU_TEXT = """Астрология — это как фотография души в момент рождения! На ней отпечатано всё: твой характер, выборы, страхи, желания. Она хранит воспоминание о том, кем ты был, зачем пришёл и куда идёшь.

Через карту можно увидеть не просто события, а смысл за ними. То, ради чего всё это случается. 💫

В ней нет приговоров, только подсказки. Звёзды не управляют тобой, они лишь показывают, где спрятана твоя сила, и что сейчас просится на свет.

Пойдём, покажу, как твоя карта оживает."""
    
    # Текст описания канала с подпиской
    SUBSCRIPTION_CHANNEL_TEXT = """💫 **Жить без надрыва** — пространство, где можно выдохнуть и понять, что с тобой всё в порядке.

Здесь мы проживаем астрологические энергии мягко, осознанно, без борьбы.

Каждую неделю ты получаешь:
✨ аудио-настройки и прогнозы проживания,
🌕 лунные порталы — новолуние и полнолуние,
🕊 практики для баланса и внутренней ясности,
💞 живую поддержку и обратную связь.

Ты начинаешь чувствовать себя как с навигатором в руках и понимаешь, что сейчас происходит, когда лучше действовать, а когда замедлиться, как проживать циклы без потери энергии и веры в себя.

Это пространство, где всё становится на свои места. 🤍

Подписка — 990₽ / месяц."""
    
    ABOUT_ME_TEXT = """
👤 **Мой путь**

Профессиональный астролог и психолог с опытом более 10 лет.

Помогаю людям:
• Познать себя через призму астрологии
• Улучшить отношения
• Найти свое призвание
• Понять жизненные циклы

Моя экспертиза основана на синтезе классической астрологии и современной психологии.

🎥 [Посмотрите интервью со мной](https://youtu.be/ZbksvyO_Olw?si=rZsk8u7ZzRcXiWh1)
"""
    

config = Config()


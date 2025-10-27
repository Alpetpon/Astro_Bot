import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import mongodb
from handlers import (
    start_router,
    menu_router,
    courses_router,
    consultations_router,
    cabinet_router,
    payments_router,
    reviews_router,
    admin_router,
    admin_guides_router,
    admin_reviews_router,
    admin_video_router,
    admin_mini_course_router,
    subscription_router,
    admin_subscriptions_router
)
from handlers.learning_handlers import learning_router
from middlewares import NavigationMiddleware
from scheduler.payment_checker import start_payment_checker, stop_payment_checker


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_sales_bot():
    """Функция запуска основного бота (воронка продаж)"""
    logger.info("Initializing sales bot...")
    
    # Создание бота и диспетчера с хранилищем для FSM
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware для навигации
    dp.callback_query.middleware(NavigationMiddleware())
    logger.info("Navigation middleware registered")
    
    # Инициализация сервисов подписок
    logger.info("Initializing subscription services...")
    from services.subscription_service import SubscriptionService
    from services.subscription_payment_service import SubscriptionPaymentService
    from handlers import subscription_handlers, admin_subscriptions
    
    subscription_service = SubscriptionService(bot)
    payment_service = SubscriptionPaymentService()
    
    # Инициализируем сервисы в обработчиках
    subscription_handlers.init_services(subscription_service, payment_service)
    admin_subscriptions.init_service(subscription_service)
    
    logger.info("✅ Subscription services initialized")
    
    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(admin_guides_router)
    dp.include_router(admin_reviews_router)
    dp.include_router(admin_video_router)
    dp.include_router(admin_mini_course_router)
    dp.include_router(admin_subscriptions_router)
    dp.include_router(subscription_router)
    dp.include_router(menu_router)
    dp.include_router(courses_router)
    dp.include_router(consultations_router)
    dp.include_router(reviews_router)
    dp.include_router(payments_router)
    dp.include_router(cabinet_router)
    
    # Запуск автоматической проверки платежей
    logger.info("Starting payment checker...")
    payment_checker = await start_payment_checker(bot, check_interval=60)
    logger.info("✅ Платежи будут автоматически проверяться каждые 60 секунд")
    
    # Запуск планировщика для подписок
    logger.info("Starting subscription scheduler...")
    from scheduler.subscription_tasks import setup_subscription_scheduler
    subscription_scheduler = setup_subscription_scheduler(bot, subscription_service)
    subscription_scheduler.start()
    logger.info("✅ Планировщик подписок запущен")
    
    # Запуск основного бота (воронка продаж)
    logger.info("💼 Sales bot started successfully!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Останавливаем проверку платежей
        await stop_payment_checker()
        
        # Останавливаем планировщик подписок
        if subscription_scheduler.running:
            subscription_scheduler.shutdown()
            logger.info("Subscription scheduler stopped")
        
        await bot.session.close()


async def run_learning_bot():
    """Функция запуска учебного бота"""
    # Проверяем наличие токена учебного бота
    if not config.LEARNING_BOT_TOKEN:
        logger.error("❌ LEARNING_BOT_TOKEN не указан в .env - учебный бот не будет запущен")
        return
    
    logger.info("Initializing learning bot...")
    
    # Создание учебного бота и диспетчера
    learning_bot = Bot(
        token=config.LEARNING_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    learning_storage = MemoryStorage()
    learning_dp = Dispatcher(storage=learning_storage)
    
    # Регистрация роутера учебного бота
    learning_dp.include_router(learning_router)
    
    # Запуск учебного бота
    logger.info("🎓 Learning bot started successfully!")
    try:
        await learning_dp.start_polling(learning_bot, allowed_updates=learning_dp.resolve_used_update_types())
    finally:
        await learning_bot.session.close()


async def fix_mongodb_index():
    """Принудительное исправление индекса payment_id перед запуском"""
    try:
        db = mongodb.get_database()
        
        # Получаем список индексов
        indexes = await db.payments.index_information()
        
        # Проверяем индекс payment_id_1
        if 'payment_id_1' in indexes:
            index_info = indexes['payment_id_1']
            
            # Если индекс не sparse - удаляем и пересоздаем
            if not index_info.get('sparse', False):
                logger.info("=" * 60)
                logger.info("🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Обнаружен старый non-sparse индекс payment_id")
                logger.info("🔧 Удаляем и пересоздаем правильный индекс...")
                logger.info("=" * 60)
                
                # Удаляем старый индекс
                await db.payments.drop_index('payment_id_1')
                logger.info("✅ Старый индекс payment_id удален")
                
                # Создаем новый sparse индекс
                await db.payments.create_index("payment_id", unique=True, sparse=True)
                logger.info("✅ Новый sparse индекс payment_id создан")
                logger.info("=" * 60)
            else:
                logger.info("✓ Индекс payment_id корректный (sparse), исправление не требуется")
        else:
            logger.info("⚠️ Индекс payment_id отсутствует, будет создан автоматически")
    
    except Exception as e:
        logger.error(f"❌ Ошибка при исправлении индекса payment_id: {e}")
        raise


async def main():
    """Главная функция - запускает оба бота одновременно"""
    try:
        # Инициализация MongoDB (общая для обоих ботов)
        logger.info(f"Connecting to MongoDB: {config.MONGODB_URL}")
        await mongodb.connect(config.MONGODB_URL, config.MONGODB_DB_NAME)
        
        # КРИТИЧЕСКИ ВАЖНО: Исправляем индекс перед запуском
        logger.info("Проверка и исправление индексов MongoDB...")
        await fix_mongodb_index()
        
        # Логируем состояние данных
        from data import get_all_courses, get_all_consultations, get_all_guides, get_mini_course
        
        courses = get_all_courses()
        consultations = get_all_consultations()
        guides = get_all_guides()
        mini_course = get_mini_course()
        
        mini_course_status = "loaded" if mini_course else "not found"
        logger.info(f"Data loaded: {len(courses)} courses, {len(consultations)} consultations, {len(guides)} guides, mini-course: {mini_course_status}")
        
        logger.info("=" * 60)
        logger.info("🚀 Запуск обоих ботов...")
        logger.info("=" * 60)
        
        # Запускаем оба бота параллельно
        await asyncio.gather(
            run_sales_bot(),
            run_learning_bot()
        )
    finally:
        await mongodb.close()
        logger.info("MongoDB connection closed")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bots stopped by user")


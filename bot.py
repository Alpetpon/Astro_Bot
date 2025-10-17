import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

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
    admin_video_router
)


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Инициализация MongoDB
    logger.info(f"Connecting to MongoDB: {config.MONGODB_URL}")
    await mongodb.connect(config.MONGODB_URL, config.MONGODB_DB_NAME)
    
    # Логируем состояние данных
    from data import get_all_courses, get_all_consultations, get_all_guides
    
    # Все данные теперь из JSON
    courses = get_all_courses()
    consultations = get_all_consultations()
    guides = get_all_guides()
    
    logger.info(f"Data loaded: {len(courses)} courses, {len(consultations)} consultations, {len(guides)} guides (all from JSON)")
    
    # Создание бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(admin_guides_router)
    dp.include_router(admin_reviews_router)
    dp.include_router(admin_video_router)
    dp.include_router(menu_router)
    dp.include_router(courses_router)
    dp.include_router(consultations_router)
    dp.include_router(reviews_router)
    dp.include_router(payments_router)
    dp.include_router(cabinet_router)
    
    # Запуск бота
    logger.info("Bot started successfully!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await mongodb.close()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


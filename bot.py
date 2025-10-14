import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from database import init_db
from handlers import (
    start_router,
    menu_router,
    courses_router,
    consultations_router,
    cabinet_router,
    payments_router,
    admin_router,
    admin_guides_router
)
from scheduler import setup_scheduler


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Инициализация базы данных
    logger.info(f"Initializing database at: {config.DATABASE_URL}")
    init_db()
    
    # Логируем состояние БД
    from database import get_db, Course, Consultation, Guide
    db = get_db()
    try:
        courses_count = db.query(Course).count()
        consultations_count = db.query(Consultation).count()
        guides_count = db.query(Guide).count()
        logger.info(f"Database stats: {courses_count} courses, {consultations_count} consultations, {guides_count} guides")
    finally:
        db.close()
    
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
    dp.include_router(menu_router)
    dp.include_router(courses_router)
    dp.include_router(consultations_router)
    dp.include_router(payments_router)
    dp.include_router(cabinet_router)
    
    # Настройка планировщика
    logger.info("Setting up scheduler...")
    scheduler = setup_scheduler(bot)
    scheduler.start()
    
    # Запуск бота
    logger.info("Bot started successfully!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


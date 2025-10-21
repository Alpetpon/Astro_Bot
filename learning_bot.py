import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import mongodb
from handlers.learning_handlers import learning_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска учебного бота"""
    # Проверяем наличие токена учебного бота
    if not config.LEARNING_BOT_TOKEN:
        logger.error("❌ LEARNING_BOT_TOKEN не указан в .env")
        return
    
    # Инициализация MongoDB (общая БД с основным ботом)
    logger.info(f"Connecting to MongoDB: {config.MONGODB_URL}")
    await mongodb.connect(config.MONGODB_URL, config.MONGODB_DB_NAME)
    
    # Логируем состояние данных
    from data import get_all_courses, get_mini_course
    
    courses = get_all_courses()
    mini_course = get_mini_course()
    
    mini_course_status = "loaded" if mini_course else "not found"
    logger.info(f"Data loaded: {len(courses)} courses, mini-course: {mini_course_status}")
    
    # Создание бота и диспетчера с хранилищем для FSM
    bot = Bot(
        token=config.LEARNING_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутера учебного бота
    dp.include_router(learning_router)
    
    # Запуск бота
    logger.info("🎓 Learning bot started successfully!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await mongodb.close()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Learning bot stopped by user")


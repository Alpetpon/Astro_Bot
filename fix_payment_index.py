"""
Скрипт для исправления индекса payment_id в коллекции payments
Удаляет старый уникальный индекс и создает новый sparse индекс
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_payment_index():
    """Исправление индекса payment_id"""
    try:
        # Подключение к MongoDB
        client = AsyncIOMotorClient(config.MONGODB_URL)
        db = client[config.MONGODB_DB_NAME]
        
        logger.info(f"Connected to MongoDB: {config.MONGODB_DB_NAME}")
        
        # Получаем список индексов
        indexes = await db.payments.index_information()
        logger.info(f"Current indexes: {list(indexes.keys())}")
        
        # Удаляем старый индекс payment_id, если он есть
        if 'payment_id_1' in indexes:
            index_info = indexes['payment_id_1']
            logger.info(f"Found payment_id_1 index: {index_info}")
            
            # Проверяем, не sparse ли он
            if not index_info.get('sparse', False):
                logger.info("Dropping old non-sparse index payment_id_1...")
                await db.payments.drop_index('payment_id_1')
                logger.info("✅ Old index dropped")
            else:
                logger.info("Index is already sparse, no need to drop")
        
        # Создаем новый sparse индекс
        logger.info("Creating new sparse unique index on payment_id...")
        await db.payments.create_index("payment_id", unique=True, sparse=True)
        logger.info("✅ New sparse index created")
        
        # Проверяем результат
        indexes = await db.payments.index_information()
        payment_id_index = indexes.get('payment_id_1', {})
        logger.info(f"Final payment_id index: {payment_id_index}")
        
        if payment_id_index.get('sparse'):
            logger.info("✅ SUCCESS: payment_id index is now sparse and unique")
        else:
            logger.error("❌ ERROR: payment_id index is not sparse!")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Error fixing index: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    asyncio.run(fix_payment_index())


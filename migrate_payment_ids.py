"""
Миграция для удаления payment_id=null из существующих документов в коллекции payments
Это нужно для совместимости со sparse unique индексом
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_payments():
    """Удаление поля payment_id из документов, где оно равно null"""
    try:
        # Подключение к MongoDB
        client = AsyncIOMotorClient(config.MONGODB_URL)
        db = client[config.MONGODB_DB_NAME]
        
        logger.info(f"Connected to MongoDB: {config.MONGODB_DB_NAME}")
        
        # Находим все документы с payment_id = null
        null_payments = await db.payments.count_documents({"payment_id": None})
        logger.info(f"Found {null_payments} payments with payment_id = null")
        
        if null_payments > 0:
            # Удаляем поле payment_id из всех документов, где оно равно null
            result = await db.payments.update_many(
                {"payment_id": None},
                {"$unset": {"payment_id": ""}}
            )
            logger.info(f"✅ Updated {result.modified_count} documents - removed payment_id field")
        else:
            logger.info("✅ No documents to migrate")
        
        # Проверяем результат
        null_payments_after = await db.payments.count_documents({"payment_id": None})
        logger.info(f"After migration: {null_payments_after} payments with payment_id = null")
        
        if null_payments_after == 0:
            logger.info("✅ SUCCESS: All payment_id=null fields removed")
        else:
            logger.warning(f"⚠️ Still have {null_payments_after} payments with payment_id = null")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Error during migration: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    asyncio.run(migrate_payments())


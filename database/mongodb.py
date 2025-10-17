"""
MongoDB подключение и утилиты
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """Класс для работы с MongoDB"""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls, connection_string: str, database_name: str = "astro_bot"):
        """Подключение к MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(connection_string)
            cls.db = cls.client[database_name]
            
            # Проверка подключения
            await cls.client.admin.command('ping')
            logger.info(f"✅ MongoDB подключена: {database_name}")
            
            # Создание индексов
            await cls._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к MongoDB: {e}")
            raise
    
    @classmethod
    async def _create_indexes(cls):
        """Создание индексов для коллекций"""
        if cls.db is None:
            return
        
        try:
            # Индексы для users
            await cls.db.users.create_index("telegram_id", unique=True)
            await cls.db.users.create_index("username")
            await cls.db.users.create_index("last_activity")
            
            # Индексы для payments
            await cls.db.payments.create_index("user_id")
            await cls.db.payments.create_index("payment_id", unique=True, sparse=True)
            await cls.db.payments.create_index("status")
            await cls.db.payments.create_index("created_at")
            
            # Индексы для bot_settings
            await cls.db.bot_settings.create_index("setting_key", unique=True)
            
            logger.info("✅ Индексы созданы")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания индексов: {e}")
    
    @classmethod
    async def close(cls):
        """Закрытие подключения"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB отключена")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Получение экземпляра базы данных"""
        if cls.db is None:
            raise RuntimeError("MongoDB не подключена. Вызовите connect() сначала.")
        return cls.db


# Глобальный экземпляр
mongodb = MongoDB()


async def get_db() -> AsyncIOMotorDatabase:
    """Получение базы данных (для совместимости с существующим кодом)"""
    return mongodb.get_database()


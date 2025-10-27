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
            # Исправление индекса payment_id (если нужно)
            await cls._fix_payment_id_index()
            
            # Индексы для users
            await cls.db.users.create_index("telegram_id", unique=True)
            await cls.db.users.create_index("username")
            await cls.db.users.create_index("last_activity")
            
            # Индексы для payments
            await cls.db.payments.create_index("user_id")
            await cls.db.payments.create_index("payment_id", unique=True, sparse=True)
            await cls.db.payments.create_index("status")
            await cls.db.payments.create_index("created_at")
            
            # Индексы для subscriptions (подписки на канал)
            await cls.db.subscriptions.create_index("user_id")
            await cls.db.subscriptions.create_index("is_active")
            await cls.db.subscriptions.create_index("end_date")
            await cls.db.subscriptions.create_index([("user_id", 1), ("is_active", 1)])
            
            # Индексы для subscription_payments (платежи за подписки)
            await cls.db.subscription_payments.create_index("payment_id", unique=True)
            await cls.db.subscription_payments.create_index("user_id")
            await cls.db.subscription_payments.create_index("status")
            
            # Индексы для bot_settings
            await cls.db.bot_settings.create_index("setting_key", unique=True)
            
            logger.info("✅ Индексы созданы")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания индексов: {e}")
    
    @classmethod
    async def _fix_payment_id_index(cls):
        """
        Автоматическое исправление индекса payment_id
        Удаляет старый non-sparse индекс и создает новый sparse индекс
        """
        try:
            # Получаем список индексов
            indexes = await cls.db.payments.index_information()
            
            # Проверяем индекс payment_id_1
            if 'payment_id_1' in indexes:
                index_info = indexes['payment_id_1']
                
                # Если индекс не sparse - удаляем и пересоздаем
                if not index_info.get('sparse', False):
                    logger.info("🔧 Обнаружен старый non-sparse индекс payment_id. Исправляем...")
                    
                    # Удаляем старый индекс
                    await cls.db.payments.drop_index('payment_id_1')
                    logger.info("✅ Старый индекс payment_id удален")
                    
                    # Создаем новый sparse индекс
                    await cls.db.payments.create_index("payment_id", unique=True, sparse=True)
                    logger.info("✅ Новый sparse индекс payment_id создан")
                else:
                    logger.debug("✓ Индекс payment_id уже sparse, исправление не требуется")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при исправлении индекса payment_id: {e}")
    
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


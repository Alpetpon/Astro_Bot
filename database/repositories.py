"""
Репозитории для работы с MongoDB
"""
from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from .mongo_models import User, Payment, BotSettings


class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.users
    
    async def create(self, user: User) -> User:
        """Создание пользователя"""
        data = user.to_dict()
        result = await self.collection.insert_one(data)
        user.id = result.inserted_id
        return user
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        data = await self.collection.find_one({"telegram_id": telegram_id})
        return User.from_dict(data) if data else None
    
    async def get_by_id(self, user_id: ObjectId) -> Optional[User]:
        """Получение пользователя по ID"""
        data = await self.collection.find_one({"_id": user_id})
        return User.from_dict(data) if data else None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Получение пользователя по username"""
        data = await self.collection.find_one({"username": username})
        return User.from_dict(data) if data else None
    
    async def update_activity(self, telegram_id: int):
        """Обновление времени последней активности"""
        await self.collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"last_activity": datetime.utcnow()}}
        )
    
    async def get_all(self) -> List[User]:
        """Получение всех пользователей"""
        cursor = self.collection.find()
        users = []
        async for data in cursor:
            users.append(User.from_dict(data))
        return users
    
    async def count(self) -> int:
        """Подсчет всех пользователей"""
        return await self.collection.count_documents({})
    
    async def count_active_since(self, since: datetime) -> int:
        """Подсчет активных пользователей с определенной даты"""
        return await self.collection.count_documents({
            "last_activity": {"$gte": since}
        })
    
    async def count_created_since(self, since: datetime) -> int:
        """Подсчет новых пользователей с определенной даты"""
        return await self.collection.count_documents({
            "created_at": {"$gte": since}
        })
    
    async def get_inactive_users(self, days: int) -> List[User]:
        """Получение неактивных пользователей за N дней"""
        threshold = datetime.utcnow() - timedelta(days=days)
        cursor = self.collection.find({"last_activity": {"$lt": threshold}})
        users = []
        async for data in cursor:
            users.append(User.from_dict(data))
        return users
    
    async def delete_by_telegram_id(self, telegram_id: int) -> bool:
        """Удаление пользователя по Telegram ID"""
        result = await self.collection.delete_one({"telegram_id": telegram_id})
        return result.deleted_count > 0


class PaymentRepository:
    """Репозиторий для работы с платежами"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.payments
    
    async def create(self, payment: Payment) -> Payment:
        """Создание платежа"""
        data = payment.to_dict()
        result = await self.collection.insert_one(data)
        payment.id = result.inserted_id
        return payment
    
    async def get_by_id(self, payment_id: ObjectId) -> Optional[Payment]:
        """Получение платежа по ID"""
        data = await self.collection.find_one({"_id": payment_id})
        return Payment.from_dict(data) if data else None
    
    async def get_by_payment_id(self, payment_id: str) -> Optional[Payment]:
        """Получение платежа по YooKassa payment_id"""
        data = await self.collection.find_one({"payment_id": payment_id})
        return Payment.from_dict(data) if data else None
    
    async def update(self, payment_id: ObjectId, updates: dict):
        """Обновление платежа"""
        await self.collection.update_one(
            {"_id": payment_id},
            {"$set": updates}
        )
    
    async def update_by_payment_id(self, payment_id: str, updates: dict):
        """Обновление платежа по YooKassa payment_id"""
        await self.collection.update_one(
            {"payment_id": payment_id},
            {"$set": updates}
        )
    
    async def get_user_payments(self, user_id: ObjectId) -> List[Payment]:
        """Получение всех платежей пользователя"""
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        payments = []
        async for data in cursor:
            payments.append(Payment.from_dict(data))
        return payments
    
    async def count_by_status(self, status: str) -> int:
        """Подсчет платежей по статусу"""
        return await self.collection.count_documents({"status": status})
    
    async def count_user_payments(self, user_id: ObjectId) -> int:
        """Подсчет платежей пользователя со статусом succeeded"""
        return await self.collection.count_documents({
            "user_id": user_id,
            "status": "succeeded"
        })
    
    async def sum_by_status(self, status: str) -> float:
        """Сумма платежей по статусу"""
        pipeline = [
            {"$match": {"status": status}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        result = await self.collection.aggregate(pipeline).to_list(1)
        return result[0]["total"] if result else 0.0
    
    async def get_payments_since(self, since: datetime, status: Optional[str] = None) -> List[Payment]:
        """Получение платежей с определенной даты"""
        query = {"created_at": {"$gte": since}}
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("created_at", -1)
        payments = []
        async for data in cursor:
            payments.append(Payment.from_dict(data))
        return payments
    
    async def count_since(self, since: datetime, status: Optional[str] = None) -> int:
        """Подсчет платежей с определенной даты"""
        query = {"created_at": {"$gte": since}}
        if status:
            query["status"] = status
        return await self.collection.count_documents(query)
    
    async def sum_since(self, since: datetime, status: Optional[str] = None) -> float:
        """Сумма платежей с определенной даты"""
        query = {"created_at": {"$gte": since}}
        if status:
            query["status"] = status
        
        pipeline = [
            {"$match": query},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        result = await self.collection.aggregate(pipeline).to_list(1)
        return result[0]["total"] if result else 0.0
    
    async def get_all(self) -> List[Payment]:
        """Получение всех платежей"""
        cursor = self.collection.find().sort("created_at", -1)
        payments = []
        async for data in cursor:
            payments.append(Payment.from_dict(data))
        return payments
    
    async def get_pending_since(self, since: datetime) -> List[dict]:
        """Получение pending платежей с определенной даты (возвращает dict)"""
        query = {
            "status": "pending",
            "created_at": {"$gte": since}
        }
        cursor = self.collection.find(query).sort("created_at", -1)
        payments = []
        async for data in cursor:
            payments.append(data)
        return payments


class BotSettingsRepository:
    """Репозиторий для работы с настройками бота"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.bot_settings
    
    async def get(self, key: str) -> Optional[BotSettings]:
        """Получение настройки по ключу"""
        data = await self.collection.find_one({"setting_key": key})
        return BotSettings.from_dict(data) if data else None
    
    async def set(self, key: str, value: str):
        """Установка настройки"""
        await self.collection.update_one(
            {"setting_key": key},
            {
                "$set": {
                    "setting_value": value,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    
    async def delete(self, key: str):
        """Удаление настройки"""
        await self.collection.delete_one({"setting_key": key})


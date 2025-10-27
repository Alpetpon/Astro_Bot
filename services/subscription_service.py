"""
Сервис для управления подписками на канал
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from aiogram import Bot

from config import config
from database.mongodb import mongodb
from database.mongo_models import Subscription, SubscriptionPayment

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Сервис для управления подписками на канал"""
    
    def __init__(self, bot: Bot):
        """
        Инициализация сервиса
        
        Args:
            bot: Экземпляр бота Aiogram
        """
        self.bot = bot
        self.channel_id = config.SUBSCRIPTION_CHANNEL_ID
        self.subscription_days = config.SUBSCRIPTION_DAYS
        
        if not self.channel_id:
            logger.warning("SUBSCRIPTION_CHANNEL_ID not configured!")
        else:
            logger.info(f"SubscriptionService initialized for channel {self.channel_id}")
    
    async def get_active_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить активную подписку пользователя
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Словарь с данными подписки или None
        """
        try:
            db = mongodb.get_database()
            subscription = await db.subscriptions.find_one({
                "user_id": user_id,
                "is_active": True,
                "end_date": {"$gt": datetime.utcnow()}
            })
            return subscription
        except Exception as e:
            logger.error(f"Error getting active subscription for user {user_id}: {e}")
            return None
    
    async def create_invite_link(self, user_id: int) -> str:
        """
        Создать уникальную пригласительную ссылку для пользователя
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Пригласительная ссылка
        """
        try:
            if not self.channel_id:
                raise ValueError("SUBSCRIPTION_CHANNEL_ID not configured")
            
            # Дата истечения ссылки
            expire_date = datetime.utcnow() + timedelta(days=self.subscription_days)
            
            # Создаем уникальную ссылку
            invite_link = await self.bot.create_chat_invite_link(
                chat_id=self.channel_id,
                name=f"Подписка для пользователя {user_id}",
                expire_date=expire_date,
                member_limit=1  # Только для одного пользователя!
            )
            
            logger.info(f"Created invite link for user {user_id}")
            return invite_link.invite_link
            
        except Exception as e:
            logger.error(f"Error creating invite link for user {user_id}: {e}")
            raise
    
    async def create_subscription(self, user_id: int, payment_id: str) -> Dict[str, Any]:
        """
        Создать подписку после успешной оплаты
        
        Args:
            user_id: Telegram ID пользователя
            payment_id: ID платежа YooKassa
            
        Returns:
            Словарь с данными созданной подписки
        """
        try:
            # Создаем пригласительную ссылку
            invite_link = await self.create_invite_link(user_id)
            
            # Даты подписки
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=self.subscription_days)
            
            # Создаем подписку
            subscription = Subscription(
                user_id=user_id,
                invite_link=invite_link,
                start_date=start_date,
                end_date=end_date,
                is_active=True,
                payment_id=payment_id
            )
            
            # Сохраняем в БД
            db = mongodb.get_database()
            result = await db.subscriptions.insert_one(subscription.to_dict())
            
            subscription_data = subscription.to_dict()
            subscription_data['_id'] = result.inserted_id
            
            logger.info(f"Created subscription for user {user_id} until {end_date}")
            return subscription_data
            
        except Exception as e:
            logger.error(f"Error creating subscription for user {user_id}: {e}")
            raise
    
    async def deactivate_subscription(self, subscription_id) -> bool:
        """
        Деактивировать подписку
        
        Args:
            subscription_id: ID подписки в MongoDB
            
        Returns:
            True если успешно деактивирована
        """
        try:
            db = mongodb.get_database()
            result = await db.subscriptions.update_one(
                {"_id": subscription_id},
                {"$set": {"is_active": False}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error deactivating subscription {subscription_id}: {e}")
            return False
    
    async def kick_user_from_channel(self, user_id: int) -> bool:
        """
        Удалить пользователя из канала
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            True если успешно удален
        """
        try:
            if not self.channel_id:
                logger.warning("SUBSCRIPTION_CHANNEL_ID not configured")
                return False
            
            # Блокируем пользователя
            await self.bot.ban_chat_member(
                chat_id=self.channel_id,
                user_id=user_id
            )
            
            # Сразу разблокируем (чтобы мог вернуться при продлении)
            await self.bot.unban_chat_member(
                chat_id=self.channel_id,
                user_id=user_id
            )
            
            logger.info(f"Kicked user {user_id} from channel")
            return True
            
        except Exception as e:
            logger.error(f"Error kicking user {user_id} from channel: {e}")
            return False
    
    async def save_payment(
        self,
        user_id: int,
        payment_id: str,
        amount: float,
        currency: str = 'RUB',
        status: str = 'pending'
    ) -> Dict[str, Any]:
        """
        Сохранить платеж за подписку в БД
        
        Args:
            user_id: Telegram ID пользователя
            payment_id: ID платежа YooKassa
            amount: Сумма платежа
            currency: Валюта
            status: Статус платежа
            
        Returns:
            Словарь с данными платежа
        """
        try:
            payment = SubscriptionPayment(
                user_id=user_id,
                payment_id=payment_id,
                amount=amount,
                currency=currency,
                status=status
            )
            
            db = mongodb.get_database()
            result = await db.subscription_payments.insert_one(payment.to_dict())
            
            payment_data = payment.to_dict()
            payment_data['_id'] = result.inserted_id
            
            logger.info(f"Saved payment {payment_id} for user {user_id}")
            return payment_data
            
        except Exception as e:
            logger.error(f"Error saving payment {payment_id}: {e}")
            raise
    
    async def update_payment_status(
        self,
        payment_id: str,
        status: str,
        paid_at: Optional[datetime] = None
    ) -> bool:
        """
        Обновить статус платежа
        
        Args:
            payment_id: ID платежа YooKassa
            status: Новый статус
            paid_at: Дата оплаты
            
        Returns:
            True если успешно обновлен
        """
        try:
            db = mongodb.get_database()
            
            update_data = {"status": status}
            if paid_at:
                update_data["paid_at"] = paid_at
            
            result = await db.subscription_payments.update_one(
                {"payment_id": payment_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating payment {payment_id}: {e}")
            return False
    
    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить платеж по ID
        
        Args:
            payment_id: ID платежа YooKassa
            
        Returns:
            Словарь с данными платежа или None
        """
        try:
            db = mongodb.get_database()
            payment = await db.subscription_payments.find_one({"payment_id": payment_id})
            return payment
        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {e}")
            return None
    
    async def link_payment_to_subscription(self, payment_id: str, subscription_id) -> bool:
        """
        Связать платеж с подпиской
        
        Args:
            payment_id: ID платежа YooKassa
            subscription_id: ID подписки в MongoDB
            
        Returns:
            True если успешно связаны
        """
        try:
            db = mongodb.get_database()
            result = await db.subscription_payments.update_one(
                {"payment_id": payment_id},
                {"$set": {"subscription_id": subscription_id}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error linking payment {payment_id} to subscription: {e}")
            return False
    
    async def get_expiring_subscriptions(self, days_before: int) -> list:
        """
        Получить подписки, которые истекают через N дней
        
        Args:
            days_before: Количество дней до истечения
            
        Returns:
            Список подписок
        """
        try:
            db = mongodb.get_database()
            
            # Границы временного окна
            now = datetime.utcnow()
            start_time = now + timedelta(days=days_before)
            end_time = start_time + timedelta(hours=1)  # Окно в 1 час
            
            # Определяем поле для проверки
            notification_field = f"notified_{days_before}_days" if days_before == 3 else f"notified_{days_before}_day"
            
            subscriptions = await db.subscriptions.find({
                "is_active": True,
                "end_date": {
                    "$gte": start_time,
                    "$lt": end_time
                },
                notification_field: False
            }).to_list(length=None)
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []
    
    async def mark_notification_sent(self, subscription_id, days_before: int) -> bool:
        """
        Пометить, что уведомление отправлено
        
        Args:
            subscription_id: ID подписки
            days_before: За сколько дней было уведомление
            
        Returns:
            True если успешно помечено
        """
        try:
            db = mongodb.get_database()
            
            # Определяем поле
            notification_field = f"notified_{days_before}_days" if days_before == 3 else f"notified_{days_before}_day"
            
            result = await db.subscriptions.update_one(
                {"_id": subscription_id},
                {"$set": {notification_field: True}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error marking notification sent: {e}")
            return False
    
    async def get_expired_subscriptions(self) -> list:
        """
        Получить истекшие подписки
        
        Returns:
            Список истекших подписок
        """
        try:
            db = mongodb.get_database()
            
            now = datetime.utcnow()
            
            subscriptions = await db.subscriptions.find({
                "is_active": True,
                "end_date": {"$lt": now}
            }).to_list(length=None)
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Error getting expired subscriptions: {e}")
            return []
    
    async def get_subscription_stats(self) -> Dict[str, Any]:
        """
        Получить статистику по подпискам
        
        Returns:
            Словарь со статистикой
        """
        try:
            db = mongodb.get_database()
            
            # Общее количество подписок
            total_subscriptions = await db.subscriptions.count_documents({})
            
            # Активные подписки
            active_subscriptions = await db.subscriptions.count_documents({
                "is_active": True,
                "end_date": {"$gt": datetime.utcnow()}
            })
            
            # Всего платежей
            total_payments = await db.subscription_payments.count_documents({})
            
            # Успешные платежи
            succeeded_payments = await db.subscription_payments.count_documents({
                "status": "succeeded"
            })
            
            # Общая сумма
            pipeline = [
                {"$match": {"status": "succeeded"}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]
            result = await db.subscription_payments.aggregate(pipeline).to_list(length=1)
            total_amount = result[0]["total"] if result else 0
            
            return {
                "total_subscriptions": total_subscriptions,
                "active_subscriptions": active_subscriptions,
                "total_payments": total_payments,
                "succeeded_payments": succeeded_payments,
                "total_amount": total_amount
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            return {
                "total_subscriptions": 0,
                "active_subscriptions": 0,
                "total_payments": 0,
                "succeeded_payments": 0,
                "total_amount": 0
            }


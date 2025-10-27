"""
Модели данных для MongoDB
"""
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId


class BaseModel:
    """Базовая модель для MongoDB документов"""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Создание экземпляра из словаря"""
        if data is None:
            return None
        return cls(**data)
    
    def to_dict(self, include_id: bool = False) -> Dict[str, Any]:
        """Преобразование в словарь"""
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if key == 'id' and not include_id:
                continue
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value
            else:
                result[key] = value
        return result


class User:
    """Модель пользователя"""
    
    def __init__(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_activity: Optional[datetime] = None,
        is_active: bool = True,
        _id: Optional[ObjectId] = None
    ):
        self.id = _id
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.created_at = created_at or datetime.utcnow()
        self.last_activity = last_activity or datetime.utcnow()
        self.is_active = is_active
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для MongoDB"""
        data = {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "is_active": self.is_active
        }
        if self.id:
            data["_id"] = self.id
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Создание из словаря MongoDB"""
        if data is None:
            return None
        return cls(
            _id=data.get("_id"),
            telegram_id=data["telegram_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            created_at=data.get("created_at"),
            last_activity=data.get("last_activity"),
            is_active=data.get("is_active", True)
        )


class Payment:
    """Модель платежа"""
    
    def __init__(
        self,
        user_id: ObjectId,
        amount: float,
        status: str = 'pending',
        currency: str = 'RUB',
        product_type: str = 'course',
        course_slug: Optional[str] = None,
        tariff_id: Optional[str] = None,
        consultation_slug: Optional[str] = None,
        consultation_option_id: Optional[str] = None,
        product_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        confirmation_url: Optional[str] = None,
        is_payment_link: bool = False,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        paid_at: Optional[datetime] = None,
        _id: Optional[ObjectId] = None
    ):
        self.id = _id
        self.user_id = user_id
        self.amount = amount
        self.status = status
        self.currency = currency
        self.product_type = product_type
        self.course_slug = course_slug
        self.tariff_id = tariff_id
        self.consultation_slug = consultation_slug
        self.consultation_option_id = consultation_option_id
        self.product_id = product_id
        self.payment_id = payment_id
        self.confirmation_url = confirmation_url
        self.is_payment_link = is_payment_link
        self.chat_id = chat_id
        self.message_id = message_id
        self.created_at = created_at or datetime.utcnow()
        self.paid_at = paid_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для MongoDB"""
        data = {
            "user_id": self.user_id,
            "amount": self.amount,
            "status": self.status,
            "currency": self.currency,
            "product_type": self.product_type,
            "course_slug": self.course_slug,
            "tariff_id": self.tariff_id,
            "consultation_slug": self.consultation_slug,
            "consultation_option_id": self.consultation_option_id,
            "product_id": self.product_id,
            "confirmation_url": self.confirmation_url,
            "is_payment_link": self.is_payment_link,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "created_at": self.created_at,
            "paid_at": self.paid_at
        }
        # Only include payment_id if it's not None (for sparse index compatibility)
        if self.payment_id is not None:
            data["payment_id"] = self.payment_id
        if self.id:
            data["_id"] = self.id
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Payment':
        """Создание из словаря MongoDB"""
        if data is None:
            return None
        return cls(
            _id=data.get("_id"),
            user_id=data["user_id"],
            amount=data["amount"],
            status=data.get("status", "pending"),
            currency=data.get("currency", "RUB"),
            product_type=data.get("product_type", "course"),
            course_slug=data.get("course_slug"),
            tariff_id=data.get("tariff_id"),
            consultation_slug=data.get("consultation_slug"),
            consultation_option_id=data.get("consultation_option_id"),
            product_id=data.get("product_id"),
            payment_id=data.get("payment_id"),
            confirmation_url=data.get("confirmation_url"),
            is_payment_link=data.get("is_payment_link", False),
            chat_id=data.get("chat_id"),
            message_id=data.get("message_id"),
            created_at=data.get("created_at"),
            paid_at=data.get("paid_at")
        )


class Subscription:
    """Модель подписки на канал"""
    
    def __init__(
        self,
        user_id: int,
        invite_link: str,
        start_date: datetime,
        end_date: datetime,
        is_active: bool = True,
        notified_3_days: bool = False,
        notified_1_day: bool = False,
        payment_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        _id: Optional[ObjectId] = None
    ):
        self.id = _id
        self.user_id = user_id
        self.invite_link = invite_link
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = is_active
        self.notified_3_days = notified_3_days
        self.notified_1_day = notified_1_day
        self.payment_id = payment_id
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для MongoDB"""
        data = {
            "user_id": self.user_id,
            "invite_link": self.invite_link,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "is_active": self.is_active,
            "notified_3_days": self.notified_3_days,
            "notified_1_day": self.notified_1_day,
            "payment_id": self.payment_id,
            "created_at": self.created_at
        }
        if self.id:
            data["_id"] = self.id
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subscription':
        """Создание из словаря MongoDB"""
        if data is None:
            return None
        return cls(
            _id=data.get("_id"),
            user_id=data["user_id"],
            invite_link=data["invite_link"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            is_active=data.get("is_active", True),
            notified_3_days=data.get("notified_3_days", False),
            notified_1_day=data.get("notified_1_day", False),
            payment_id=data.get("payment_id"),
            created_at=data.get("created_at")
        )


class SubscriptionPayment:
    """Модель платежа за подписку на канал (отдельно от обычных платежей)"""
    
    def __init__(
        self,
        user_id: int,
        payment_id: str,
        amount: float,
        currency: str = 'RUB',
        status: str = 'pending',
        created_at: Optional[datetime] = None,
        paid_at: Optional[datetime] = None,
        subscription_id: Optional[ObjectId] = None,
        _id: Optional[ObjectId] = None
    ):
        self.id = _id
        self.user_id = user_id
        self.payment_id = payment_id
        self.amount = amount
        self.currency = currency
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.paid_at = paid_at
        self.subscription_id = subscription_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для MongoDB"""
        data = {
            "user_id": self.user_id,
            "payment_id": self.payment_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "created_at": self.created_at,
            "paid_at": self.paid_at,
            "subscription_id": self.subscription_id
        }
        if self.id:
            data["_id"] = self.id
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionPayment':
        """Создание из словаря MongoDB"""
        if data is None:
            return None
        return cls(
            _id=data.get("_id"),
            user_id=data["user_id"],
            payment_id=data["payment_id"],
            amount=data["amount"],
            currency=data.get("currency", "RUB"),
            status=data.get("status", "pending"),
            created_at=data.get("created_at"),
            paid_at=data.get("paid_at"),
            subscription_id=data.get("subscription_id")
        )


class BotSettings:
    """Модель настроек бота"""
    
    def __init__(
        self,
        setting_key: str,
        setting_value: Optional[str] = None,
        updated_at: Optional[datetime] = None,
        _id: Optional[ObjectId] = None
    ):
        self.id = _id
        self.setting_key = setting_key
        self.setting_value = setting_value
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для MongoDB"""
        data = {
            "setting_key": self.setting_key,
            "setting_value": self.setting_value,
            "updated_at": self.updated_at
        }
        if self.id:
            data["_id"] = self.id
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotSettings':
        """Создание из словаря MongoDB"""
        if data is None:
            return None
        return cls(
            _id=data.get("_id"),
            setting_key=data["setting_key"],
            setting_value=data.get("setting_value"),
            updated_at=data.get("updated_at")
        )


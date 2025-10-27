from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Связи
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.telegram_id}>"


class Payment(Base):
    """Модель платежа"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Теперь храним slug/id вместо FK (данные в JSON)
    course_slug = Column(String(100), nullable=True)  # slug курса из JSON
    tariff_id = Column(String(100), nullable=True)  # id тарифа из JSON
    consultation_slug = Column(String(100), nullable=True)  # slug консультации из JSON
    consultation_option_id = Column(String(100), nullable=True)  # id опции из JSON
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='RUB')
    status = Column(String(50), default='pending')  # pending, succeeded, canceled
    payment_id = Column(String(255), unique=True, nullable=True)  # ID платежа в ЮKassa
    confirmation_url = Column(String(500), nullable=True)
    product_type = Column(String(50), default='course')  # course, consultation, tarot, guide
    product_id = Column(String(100), nullable=True)  # ID продукта (универсальный)
    is_payment_link = Column(Boolean, default=False)  # Платеж создан через админ-ссылку
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment {self.payment_id} - {self.status}>"


class Subscription(Base):
    """Модель подписки с автопродлением"""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Информация о подписке
    subscription_type = Column(String(50), nullable=False)  # 'monthly', 'yearly', etc.
    status = Column(String(20), default='active')  # active, paused, canceled, expired
    auto_renewal = Column(Boolean, default=True)  # Включено ли автопродление
    
    # Даты
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)  # Дата окончания подписки
    next_payment_date = Column(DateTime, nullable=True)  # Дата следующего платежа
    last_payment_date = Column(DateTime, nullable=True)  # Дата последнего платежа
    
    # Платежная информация
    amount = Column(Float, nullable=False)  # Сумма подписки
    currency = Column(String(10), default='RUB')
    payment_id = Column(String(255), nullable=True)  # ID последнего платежа в ЮKassa
    subscription_id = Column(String(255), nullable=True)  # ID подписки в ЮKassa (если поддерживается)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", backref="subscriptions")
    
    def __repr__(self):
        return f"<Subscription {self.id} - {self.status}>"
    
    @property
    def is_active(self):
        """Проверяет, активна ли подписка"""
        return self.status == 'active' and datetime.utcnow() < self.end_date
    
    @property
    def days_remaining(self):
        """Количество дней до окончания подписки"""
        if not self.is_active:
            return 0
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)


class BotSettings(Base):
    """Модель настроек бота"""
    __tablename__ = 'bot_settings'
    
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BotSettings {self.setting_key}>"

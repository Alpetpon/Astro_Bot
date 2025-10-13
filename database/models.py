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
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.telegram_id}>"


class Course(Base):
    """Модель курса"""
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    program = Column(Text, nullable=True)  # JSON строка с программой курса
    duration = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    tariffs = relationship("Tariff", back_populates="course", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Course {self.name}>"


class Tariff(Base):
    """Модель тарифа курса"""
    __tablename__ = 'tariffs'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    with_support = Column(Boolean, default=False)
    features = Column(Text, nullable=True)  # JSON строка с особенностями тарифа
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    
    # Связи
    course = relationship("Course", back_populates="tariffs")
    payments = relationship("Payment", back_populates="tariff")
    
    def __repr__(self):
        return f"<Tariff {self.name} - {self.price}>"


class Lesson(Base):
    """Модель урока"""
    __tablename__ = 'lessons'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    module_number = Column(Integer, nullable=False)
    lesson_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Текстовый контент урока
    video_url = Column(String(500), nullable=True)
    materials = Column(Text, nullable=True)  # JSON строка с доп. материалами
    duration = Column(String(50), nullable=True)
    order = Column(Integer, default=0)
    is_free = Column(Boolean, default=False)  # Бесплатный урок для ознакомления
    
    # Связи
    course = relationship("Course", back_populates="lessons")
    progress = relationship("UserProgress", back_populates="lesson", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lesson M{self.module_number}L{self.lesson_number} - {self.title}>"


class UserProgress(Base):
    """Модель прогресса пользователя"""
    __tablename__ = 'user_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    is_completed = Column(Boolean, default=False)
    is_available = Column(Boolean, default=False)  # Доступен ли урок
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress")
    
    def __repr__(self):
        return f"<UserProgress user={self.user_id} lesson={self.lesson_id}>"


class Payment(Base):
    """Модель платежа"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=True)  # Может быть NULL для гайдов
    tariff_id = Column(Integer, ForeignKey('tariffs.id'), nullable=True)  # Может быть NULL для гайдов
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='RUB')
    status = Column(String(50), default='pending')  # pending, succeeded, canceled
    payment_id = Column(String(255), unique=True, nullable=True)  # ID платежа в ЮKassa
    confirmation_url = Column(String(500), nullable=True)
    product_type = Column(String(50), default='course')  # course, guide, consultation
    product_id = Column(String(100), nullable=True)  # ID продукта (guide_id для гайдов)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="payments")
    tariff = relationship("Tariff", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment {self.payment_id} - {self.status}>"


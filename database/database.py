from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import config

# Создание движка базы данных
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
    echo=False
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def init_db():
    """Инициализация базы данных"""
    from .models import Base
    Base.metadata.create_all(bind=engine)


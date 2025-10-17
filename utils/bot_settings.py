"""Helper функции для работы с настройками бота"""
from typing import Optional
from sqlalchemy.orm import Session
from database import BotSettings, get_db


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Получить значение настройки из базы данных
    
    Args:
        key: ключ настройки
        default: значение по умолчанию, если настройка не найдена
    
    Returns:
        Значение настройки или default
    """
    db: Session = get_db()
    try:
        setting = db.query(BotSettings).filter(BotSettings.setting_key == key).first()
        if setting:
            return setting.setting_value
        return default
    finally:
        db.close()


def set_setting(key: str, value: Optional[str]) -> bool:
    """
    Установить значение настройки в базе данных
    
    Args:
        key: ключ настройки
        value: значение настройки
    
    Returns:
        True если успешно, False если ошибка
    """
    db: Session = get_db()
    try:
        setting = db.query(BotSettings).filter(BotSettings.setting_key == key).first()
        
        if setting:
            # Обновляем существующую настройку
            setting.setting_value = value
        else:
            # Создаем новую настройку
            setting = BotSettings(
                setting_key=key,
                setting_value=value
            )
            db.add(setting)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error setting {key}: {e}")
        return False
    finally:
        db.close()


def delete_setting(key: str) -> bool:
    """
    Удалить настройку из базы данных
    
    Args:
        key: ключ настройки
    
    Returns:
        True если успешно, False если ошибка
    """
    db: Session = get_db()
    try:
        setting = db.query(BotSettings).filter(BotSettings.setting_key == key).first()
        
        if setting:
            db.delete(setting)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting {key}: {e}")
        return False
    finally:
        db.close()


# Константы для ключей настроек
WELCOME_VIDEO_KEY = "welcome_video_file_id"
ABOUT_ME_VIDEO_KEY = "about_me_video_file_id"


def is_admin(user_id: int) -> bool:
    """
    Проверка, является ли пользователь администратором
    
    Args:
        user_id: Telegram ID пользователя
    
    Returns:
        True если пользователь является администратором
    """
    from config import config
    return user_id in config.ADMIN_IDS


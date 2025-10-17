"""Helper функции для работы с настройками бота"""
from typing import Optional
from database import get_db, BotSettingsRepository


async def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Получить значение настройки из базы данных
    
    Args:
        key: ключ настройки
        default: значение по умолчанию, если настройка не найдена
    
    Returns:
        Значение настройки или default
    """
    db = await get_db()
    settings_repo = BotSettingsRepository(db)
    setting = await settings_repo.get(key)
    if setting:
        return setting.setting_value
    return default


async def set_setting(key: str, value: Optional[str]) -> bool:
    """
    Установить значение настройки в базе данных
    
    Args:
        key: ключ настройки
        value: значение настройки
    
    Returns:
        True если успешно, False если ошибка
    """
    try:
        db = await get_db()
        settings_repo = BotSettingsRepository(db)
        await settings_repo.set(key, value)
        return True
    except Exception as e:
        print(f"Error setting {key}: {e}")
        return False


async def delete_setting(key: str) -> bool:
    """
    Удалить настройку из базы данных
    
    Args:
        key: ключ настройки
    
    Returns:
        True если успешно, False если ошибка
    """
    try:
        db = await get_db()
        settings_repo = BotSettingsRepository(db)
        await settings_repo.delete(key)
        return True
    except Exception as e:
        print(f"Error deleting {key}: {e}")
        return False


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


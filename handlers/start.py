from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session

from config import config
from database import get_db, User
from keyboards import get_start_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    db: Session = get_db()
    
    try:
        # Проверяем, есть ли пользователь в базе
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            # Создаем нового пользователя
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            db.add(user)
            db.commit()
        else:
            # Обновляем активность
            user.last_activity = datetime.utcnow()
            db.commit()
        
        await message.answer(
            config.WELCOME_TEXT,
            reply_markup=get_start_keyboard()
        )
    
    finally:
        db.close()


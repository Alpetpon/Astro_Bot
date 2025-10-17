from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session

from config import config
from database import get_db, User
from keyboards import get_start_keyboard
from utils.bot_settings import get_setting, WELCOME_VIDEO_KEY

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
        
        # Получаем file_id видео (сначала из БД, потом из config)
        welcome_video_id = get_setting(WELCOME_VIDEO_KEY) or config.WELCOME_VIDEO_FILE_ID
        
        # Отправляем приветственное видео, если оно настроено
        if welcome_video_id:
            try:
                await message.answer_video(
                    video=welcome_video_id,
                    caption=config.WELCOME_TEXT,
                    reply_markup=get_start_keyboard()
                )
            except Exception as e:
                # Если видео не отправилось, отправляем обычный текст
                await message.answer(
                    config.WELCOME_TEXT,
                    reply_markup=get_start_keyboard()
                )
        else:
            # Если видео не настроено, отправляем обычный текст
            await message.answer(
                config.WELCOME_TEXT,
                reply_markup=get_start_keyboard()
            )
    
    finally:
        db.close()


@router.callback_query(F.data == "start_back")
async def back_to_start(callback: CallbackQuery):
    """Возврат к приветственному сообщению"""
    # Получаем file_id видео (сначала из БД, потом из config)
    welcome_video_id = get_setting(WELCOME_VIDEO_KEY) or config.WELCOME_VIDEO_FILE_ID
    
    try:
        # Удаляем предыдущее сообщение
        await callback.message.delete()
        
        # Отправляем приветственное видео, если оно настроено
        if welcome_video_id:
            try:
                await callback.message.answer_video(
                    video=welcome_video_id,
                    caption=config.WELCOME_TEXT,
                    reply_markup=get_start_keyboard()
                )
            except Exception as e:
                # Если видео не отправилось, отправляем обычный текст
                await callback.message.answer(
                    config.WELCOME_TEXT,
                    reply_markup=get_start_keyboard()
                )
        else:
            # Если видео не настроено, отправляем обычный текст
            await callback.message.answer(
                config.WELCOME_TEXT,
                reply_markup=get_start_keyboard()
            )
    except Exception:
        # Если не можем удалить сообщение, просто редактируем
        await callback.message.edit_text(
            config.WELCOME_TEXT,
            reply_markup=get_start_keyboard()
        )
    
    await callback.answer()


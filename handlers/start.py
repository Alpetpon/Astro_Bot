from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from config import config
from database import get_db, User, UserRepository
from keyboards import get_main_menu_keyboard
from utils.bot_settings import get_setting, WELCOME_VIDEO_KEY

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    db = await get_db()
    user_repo = UserRepository(db)
    
    # Проверяем, есть ли пользователь в базе
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    
    if not user:
        # Создаем нового пользователя
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        await user_repo.create(user)
    else:
        # Обновляем активность
        await user_repo.update_activity(message.from_user.id)
    
    # Получаем file_id видео (сначала из БД, потом из config)
    welcome_video_id = await get_setting(WELCOME_VIDEO_KEY) or config.WELCOME_VIDEO_FILE_ID
    
    # Отправляем приветственное видео с подписью и кнопками меню
    if welcome_video_id:
        try:
            await message.answer_video(
                video=welcome_video_id,
                caption=config.MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard()
            )
        except Exception:
            # Если не удалось отправить видео, отправляем только текст
            await message.answer(
                config.MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard()
            )
    else:
        # Если видео не настроено, отправляем только текст
        await message.answer(
            config.MAIN_MENU_TEXT,
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "start_back")
async def back_to_start(callback: CallbackQuery):
    """Возврат к приветственному сообщению"""
    # Получаем file_id видео (сначала из БД, потом из config)
    welcome_video_id = await get_setting(WELCOME_VIDEO_KEY) or config.WELCOME_VIDEO_FILE_ID
    
    try:
        # Удаляем предыдущее сообщение
        await callback.message.delete()
    except Exception:
        pass
    
    # Отправляем приветственное видео с подписью и кнопками
    if welcome_video_id:
        try:
            await callback.message.answer_video(
                video=welcome_video_id,
                caption=config.MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard()
            )
        except Exception:
            # Если не удалось отправить видео, отправляем только текст
            await callback.message.answer(
                config.MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard()
            )
    else:
        # Если видео не настроено, отправляем только текст
        await callback.message.answer(
            config.MAIN_MENU_TEXT,
            reply_markup=get_main_menu_keyboard()
        )
    
    await callback.answer()


"""Обработчики админ-панели для управления видео"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

from config import config
from keyboards.keyboards import get_video_settings_keyboard, get_back_to_admin_keyboard
from utils.bot_settings import (
    get_setting, set_setting, delete_setting, 
    WELCOME_VIDEO_KEY, ABOUT_ME_VIDEO_KEY, is_admin
)

router = Router()


class VideoUpload(StatesGroup):
    """Состояния для загрузки видео"""
    waiting_for_welcome_video = State()
    waiting_for_about_me_video = State()


@router.callback_query(F.data == "admin_video_settings")
async def show_video_settings(callback: CallbackQuery):
    """Показать настройки видео"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Проверяем наличие видео в БД
    welcome_video = get_setting(WELCOME_VIDEO_KEY)
    about_me_video = get_setting(ABOUT_ME_VIDEO_KEY)
    
    has_welcome = bool(welcome_video)
    has_about_me = bool(about_me_video)
    
    text = "🎥 <b>Настройки видео</b>\n\n"
    
    if has_welcome:
        text += "✅ Приветственное видео загружено\n"
    else:
        text += "❌ Приветственное видео не загружено\n"
    
    if has_about_me:
        text += "✅ Видео-интервью 'Обо мне' загружено\n"
    else:
        text += "❌ Видео-интервью 'Обо мне' не загружено\n"
    
    text += "\nВыберите действие:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_video_settings_keyboard(has_welcome, has_about_me)
    )
    await callback.answer()


# ===== ПРИВЕТСТВЕННОЕ ВИДЕО =====

@router.callback_query(F.data == "video_welcome_upload")
async def upload_welcome_video(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку приветственного видео"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📤 <b>Загрузка приветственного видео</b>\n\n"
        "Отправьте видео, которое будет показываться пользователям после команды /start\n\n"
        "Отправьте /cancel для отмены",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(VideoUpload.waiting_for_welcome_video)
    await callback.answer()


@router.message(VideoUpload.waiting_for_welcome_video, F.video)
async def save_welcome_video(message: Message, state: FSMContext):
    """Сохранить приветственное видео"""
    if not is_admin(message.from_user.id):
        return
    
    file_id = message.video.file_id
    
    # Сохраняем в БД
    success = set_setting(WELCOME_VIDEO_KEY, file_id)
    
    if success:
        await message.answer(
            "✅ <b>Приветственное видео успешно сохранено!</b>\n\n"
            f"File ID: <code>{file_id}</code>\n\n"
            "Теперь это видео будет отправляться пользователям при команде /start",
            reply_markup=get_back_to_admin_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении видео</b>\n\n"
            "Попробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.message(VideoUpload.waiting_for_welcome_video)
async def invalid_welcome_video(message: Message):
    """Обработка неверного формата"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "❌ Пожалуйста, отправьте видео (не ссылку, не документ)\n\n"
        "Или отправьте /cancel для отмены"
    )


@router.callback_query(F.data == "video_welcome_delete")
async def delete_welcome_video(callback: CallbackQuery):
    """Удалить приветственное видео"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = delete_setting(WELCOME_VIDEO_KEY)
    
    if success:
        await callback.answer("✅ Приветственное видео удалено", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)
    
    # Обновляем экран
    await show_video_settings(callback)


# ===== ВИДЕО "ОБО МНЕ" =====

@router.callback_query(F.data == "video_about_me_upload")
async def upload_about_me_video(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку видео 'Обо мне'"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📤 <b>Загрузка видео-интервью 'Обо мне'</b>\n\n"
        "Отправьте видео, которое будет показываться в разделе 'Обо мне'\n\n"
        "Отправьте /cancel для отмены",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(VideoUpload.waiting_for_about_me_video)
    await callback.answer()


@router.message(VideoUpload.waiting_for_about_me_video, F.video)
async def save_about_me_video(message: Message, state: FSMContext):
    """Сохранить видео 'Обо мне'"""
    if not is_admin(message.from_user.id):
        return
    
    file_id = message.video.file_id
    
    # Сохраняем в БД
    success = set_setting(ABOUT_ME_VIDEO_KEY, file_id)
    
    if success:
        await message.answer(
            "✅ <b>Видео-интервью 'Обо мне' успешно сохранено!</b>\n\n"
            f"File ID: <code>{file_id}</code>\n\n"
            "Теперь это видео будет отправляться пользователям в разделе 'Обо мне'",
            reply_markup=get_back_to_admin_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении видео</b>\n\n"
            "Попробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.message(VideoUpload.waiting_for_about_me_video)
async def invalid_about_me_video(message: Message):
    """Обработка неверного формата"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "❌ Пожалуйста, отправьте видео (не ссылку, не документ)\n\n"
        "Или отправьте /cancel для отмены"
    )


@router.callback_query(F.data == "video_about_me_delete")
async def delete_about_me_video(callback: CallbackQuery):
    """Удалить видео 'Обо мне'"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = delete_setting(ABOUT_ME_VIDEO_KEY)
    
    if success:
        await callback.answer("✅ Видео 'Обо мне' удалено", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)
    
    # Обновляем экран
    await show_video_settings(callback)


# ===== ОТМЕНА =====

@router.message(F.text == "/cancel", StateFilter(VideoUpload))
async def cancel_upload(message: Message, state: FSMContext):
    """Отменить загрузку видео"""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer(
        "❌ Загрузка отменена",
        reply_markup=get_back_to_admin_keyboard()
    )


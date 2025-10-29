"""Обработчики админ-панели для управления видео"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

from config import config
from keyboards.keyboards import get_video_settings_keyboard, get_back_to_admin_keyboard, get_back_to_free_course_keyboard
from utils.bot_settings import (
    get_setting, set_setting, delete_setting, 
    WELCOME_VIDEO_KEY, is_admin
)

router = Router()

# Ключи для хранения видео и фото в БД
FREE_COURSE_ZET9_VIDEO_KEY = "free_course_zet9_video"
FREE_COURSE_STEP3_PHOTOS_KEY = "free_course_step3_photos"
FREE_COURSE_STEP3_VIDEO_KEY = "free_course_step3_video"
FREE_COURSE_FINAL_MESSAGE_KEY = "free_course_final_message"

# Ключи для текстов шагов
FREE_COURSE_STEP1_TEXT_KEY = "free_course_step1_text"
FREE_COURSE_STEP2_TEXT_KEY = "free_course_step2_text"
FREE_COURSE_STEP3_TEXT_KEY = "free_course_step3_text"


class VideoUpload(StatesGroup):
    """Состояния для загрузки видео"""
    waiting_for_welcome_video = State()
    waiting_for_zet9_video = State()
    waiting_for_step3_photos = State()
    waiting_for_step3_video = State()
    waiting_for_final_message = State()
    waiting_for_step1_text = State()
    waiting_for_step2_text = State()
    waiting_for_step3_text = State()


@router.callback_query(F.data == "admin_video_settings")
async def show_video_settings(callback: CallbackQuery):
    """Показать настройки видео"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Проверяем наличие видео в БД
    welcome_video = await get_setting(WELCOME_VIDEO_KEY)
    zet9_video = await get_setting(FREE_COURSE_ZET9_VIDEO_KEY)
    step3_photos = await get_setting(FREE_COURSE_STEP3_PHOTOS_KEY)
    step3_video = await get_setting(FREE_COURSE_STEP3_VIDEO_KEY)
    final_message = await get_setting(FREE_COURSE_FINAL_MESSAGE_KEY)
    
    has_welcome = bool(welcome_video)
    has_zet9 = bool(zet9_video)
    has_step3_photos = bool(step3_photos)
    has_step3_video = bool(step3_video)
    has_final_message = bool(final_message)
    
    text = "🎥 <b>Настройки видео и фото</b>\n\n"
    text += "<b>Основные видео:</b>\n"
    
    if has_welcome:
        text += "✅ Приветственное видео загружено\n"
    else:
        text += "❌ Приветственное видео не загружено\n"
    
    text += "\n<b>Бесплатный курс - Шаг 3 (Инструкция Sotis):</b>\n"
    
    if has_step3_photos:
        import json
        try:
            photos = json.loads(step3_photos)
            text += f"✅ Фото загружено ({len(photos)} шт.)\n"
        except:
            text += "✅ Фото загружено\n"
    else:
        text += "❌ Фото не загружено\n"
    
    if has_step3_video:
        text += "✅ Видео загружено\n"
    else:
        text += "❌ Видео не загружено\n"
    
    text += "\n<b>Финальное сообщение (после кнопки 'Получилось'):</b>\n"
    
    if has_final_message:
        text += "✅ Текст настроен\n"
    else:
        text += "❌ Используется стандартный текст\n"
    
    text += "\n💡 Для шага 3 можно загрузить либо фото (несколько), либо видео"
    text += "\nВыберите действие:"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_video_settings_keyboard(has_welcome, has_step3_photos, has_step3_video, has_final_message)
        )
    except Exception:
        # Игнорируем ошибку если сообщение не изменилось
        pass
    
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
    success = await set_setting(WELCOME_VIDEO_KEY, file_id)
    
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
    
    success = await delete_setting(WELCOME_VIDEO_KEY)
    
    if success:
        await callback.answer("✅ Приветственное видео удалено")
        # Обновляем экран с новым содержимым
        await show_video_settings(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ===== ВИДЕО ZET 9 (БЕСПЛАТНЫЙ КУРС) =====

@router.callback_query(F.data == "video_zet9_upload")
async def upload_zet9_video(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку видео ZET 9"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📤 <b>Загрузка видео 'Как установить ZET 9'</b>\n\n"
        "Отправьте видео, которое будет показываться на 3-м шаге бесплатного курса\n\n"
        "Отправьте /cancel для отмены",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(VideoUpload.waiting_for_zet9_video)
    await callback.answer()


@router.message(VideoUpload.waiting_for_zet9_video, F.video)
async def save_zet9_video(message: Message, state: FSMContext):
    """Сохранить видео ZET 9"""
    if not is_admin(message.from_user.id):
        return
    
    file_id = message.video.file_id
    
    # Сохраняем в БД
    success = await set_setting(FREE_COURSE_ZET9_VIDEO_KEY, file_id)
    
    if success:
        await message.answer(
            "✅ <b>Видео ZET 9 успешно сохранено!</b>\n\n"
            f"File ID: <code>{file_id}</code>\n\n"
            "Теперь это видео будет отправляться на 3-м шаге бесплатного курса",
            reply_markup=get_back_to_admin_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении видео</b>\n\n"
            "Попробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.message(VideoUpload.waiting_for_zet9_video)
async def invalid_zet9_video(message: Message):
    """Обработка неверного формата для видео ZET 9"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "❌ Пожалуйста, отправьте видео (не ссылку, не документ)\n\n"
        "Или отправьте /cancel для отмены"
    )


@router.callback_query(F.data == "video_zet9_delete")
async def delete_zet9_video(callback: CallbackQuery):
    """Удалить видео ZET 9"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = await delete_setting(FREE_COURSE_ZET9_VIDEO_KEY)
    
    if success:
        await callback.answer("✅ Видео ZET 9 удалено")
        # Обновляем экран с новым содержимым
        await show_video_settings(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ===== ФОТО ДЛЯ ШАГА 3 (ИНСТРУКЦИЯ SOTIS) =====

@router.callback_query(F.data == "video_step3_photos_upload")
async def upload_step3_photos(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку фото для шага 3"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📤 <b>Загрузка фото для шага 3 'Инструкция Sotis'</b>\n\n"
        "Отправьте фото (можно несколько). Они будут показаны пользователям на 3-м шаге бесплатного курса.\n\n"
        "После загрузки всех фото отправьте /done\n"
        "Отправьте /cancel для отмены",
        reply_markup=get_back_to_free_course_keyboard()
    )
    
    # Инициализируем пустой список для фото
    await state.update_data(photos=[])
    await state.set_state(VideoUpload.waiting_for_step3_photos)
    await callback.answer()


@router.message(VideoUpload.waiting_for_step3_photos, F.photo)
async def save_step3_photo(message: Message, state: FSMContext):
    """Сохранить фото для шага 3"""
    if not is_admin(message.from_user.id):
        return
    
    file_id = message.photo[-1].file_id
    
    # Получаем текущий список фото
    data = await state.get_data()
    photos = data.get('photos', [])
    photos.append(file_id)
    
    # Сохраняем обновленный список
    await state.update_data(photos=photos)
    
    await message.answer(
        f"✅ Фото {len(photos)} добавлено!\n\n"
        "Отправьте еще фото или /done для завершения"
    )


@router.message(VideoUpload.waiting_for_step3_photos, F.text == "/done")
async def finish_step3_photos(message: Message, state: FSMContext):
    """Завершить загрузку фото для шага 3"""
    if not is_admin(message.from_user.id):
        return
    
    # Получаем список фото
    data = await state.get_data()
    photos = data.get('photos', [])
    
    if not photos:
        await message.answer(
            "❌ Вы не загрузили ни одного фото\n\n"
            "Отправьте фото или /cancel для отмены"
        )
        return
    
    # Сохраняем в БД как JSON
    import json
    photos_json = json.dumps(photos)
    success = await set_setting(FREE_COURSE_STEP3_PHOTOS_KEY, photos_json)
    
    if success:
        await message.answer(
            f"✅ <b>Успешно сохранено {len(photos)} фото!</b>\n\n"
            "Теперь они будут показываться на 3-м шаге бесплатного курса",
            reply_markup=get_back_to_free_course_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении фото</b>\n\n"
            "Попробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.message(VideoUpload.waiting_for_step3_photos)
async def invalid_step3_photo(message: Message):
    """Обработка неверного формата для фото шага 3"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "❌ Пожалуйста, отправьте фото\n\n"
        "Или отправьте /done для завершения\n"
        "Или /cancel для отмены"
    )


@router.callback_query(F.data == "video_step3_photos_delete")
async def delete_step3_photos(callback: CallbackQuery):
    """Удалить фото шага 3"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = await delete_setting(FREE_COURSE_STEP3_PHOTOS_KEY)
    
    if success:
        await callback.answer("✅ Фото удалены")
        # Возвращаемся к управлению бесплатным курсом
        from handlers.admin import manage_free_course
        await manage_free_course(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ===== ВИДЕО ДЛЯ ШАГА 3 (ИНСТРУКЦИЯ SOTIS) =====

@router.callback_query(F.data == "video_step3_video_upload")
async def upload_step3_video(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку видео для шага 3"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📤 <b>Загрузка видео для шага 3 'Инструкция Sotis'</b>\n\n"
        "Отправьте видео, которое будет показываться на 3-м шаге бесплатного курса\n\n"
        "Отправьте /cancel для отмены",
        reply_markup=get_back_to_free_course_keyboard()
    )
    await state.set_state(VideoUpload.waiting_for_step3_video)
    await callback.answer()


@router.message(VideoUpload.waiting_for_step3_video, F.video)
async def save_step3_video(message: Message, state: FSMContext):
    """Сохранить видео для шага 3"""
    if not is_admin(message.from_user.id):
        return
    
    file_id = message.video.file_id
    
    # Сохраняем в БД
    success = await set_setting(FREE_COURSE_STEP3_VIDEO_KEY, file_id)
    
    if success:
        await message.answer(
            "✅ <b>Видео успешно сохранено!</b>\n\n"
            f"File ID: <code>{file_id}</code>\n\n"
            "Теперь это видео будет отправляться на 3-м шаге бесплатного курса",
            reply_markup=get_back_to_free_course_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении видео</b>\n\n"
            "Попробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.message(VideoUpload.waiting_for_step3_video)
async def invalid_step3_video(message: Message):
    """Обработка неверного формата для видео шага 3"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "❌ Пожалуйста, отправьте видео (не ссылку, не документ)\n\n"
        "Или отправьте /cancel для отмены"
    )


@router.callback_query(F.data == "video_step3_video_delete")
async def delete_step3_video(callback: CallbackQuery):
    """Удалить видео шага 3"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = await delete_setting(FREE_COURSE_STEP3_VIDEO_KEY)
    
    if success:
        await callback.answer("✅ Видео удалено")
        # Возвращаемся к управлению бесплатным курсом
        from handlers.admin import manage_free_course
        await manage_free_course(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ===== ФИНАЛЬНОЕ СООБЩЕНИЕ (ПОСЛЕ КНОПКИ "ПОЛУЧИЛОСЬ") =====

@router.callback_query(F.data == "free_course_final_message_edit")
async def edit_final_message(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование финального сообщения"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем текущий текст
    current_text = await get_setting(FREE_COURSE_FINAL_MESSAGE_KEY)
    
    text = "✏️ <b>Редактирование финального сообщения</b>\n\n"
    
    if current_text:
        text += "📝 <b>Текущий текст:</b>\n"
        text += f"<code>{current_text[:500]}...</code>\n\n" if len(current_text) > 500 else f"<code>{current_text}</code>\n\n"
    else:
        text += "📝 Сейчас используется стандартный текст\n\n"
    
    text += "Отправьте новый текст для финального сообщения (которое показывается после кнопки 'Получилось')\n\n"
    text += "💡 Вы можете использовать эмодзи и форматирование\n\n"
    text += "Отправьте /cancel для отмены"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_free_course_keyboard()
    )
    await state.set_state(VideoUpload.waiting_for_final_message)
    await callback.answer()


@router.message(VideoUpload.waiting_for_final_message, F.text)
async def save_final_message(message: Message, state: FSMContext):
    """Сохранить финальное сообщение"""
    if not is_admin(message.from_user.id):
        return
    
    # Проверяем, не команда ли это
    if message.text.startswith('/'):
        return
    
    new_text = message.text
    
    # Сохраняем в БД
    success = await set_setting(FREE_COURSE_FINAL_MESSAGE_KEY, new_text)
    
    if success:
        preview = new_text[:200] + "..." if len(new_text) > 200 else new_text
        await message.answer(
            f"✅ <b>Финальное сообщение успешно сохранено!</b>\n\n"
            f"📝 <b>Предпросмотр:</b>\n{preview}\n\n"
            "Теперь это сообщение будет показываться пользователям после кнопки 'Получилось'",
            reply_markup=get_back_to_free_course_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении текста</b>\n\n"
            "Попробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "free_course_final_message_delete")
async def delete_final_message(callback: CallbackQuery):
    """Удалить финальное сообщение (вернуться к стандартному)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = await delete_setting(FREE_COURSE_FINAL_MESSAGE_KEY)
    
    if success:
        await callback.answer("✅ Текст удален, будет использоваться стандартный")
        # Возвращаемся к управлению бесплатным курсом
        from handlers.admin import manage_free_course
        await manage_free_course(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ===== РЕДАКТИРОВАНИЕ ТЕКСТОВ ШАГОВ =====

# ШАГ 1
@router.callback_query(F.data == "free_course_step1_edit")
async def edit_step1_text(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование текста Шага 1"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    current_text = await get_setting(FREE_COURSE_STEP1_TEXT_KEY)
    
    text = "✏️ <b>Редактирование текста Шага 1 (Вступление)</b>\n\n"
    
    if current_text:
        text += f"📝 <b>Текущий текст:</b>\n<code>{current_text[:300]}...</code>\n\n" if len(current_text) > 300 else f"📝 <b>Текущий текст:</b>\n<code>{current_text}</code>\n\n"
    else:
        text += "📝 Сейчас используется стандартный текст\n\n"
    
    text += "Отправьте новый текст для Шага 1\n\n"
    text += "💡 Вы можете использовать эмодзи и форматирование\n"
    text += "Отправьте /cancel для отмены"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_free_course_keyboard())
    await state.set_state(VideoUpload.waiting_for_step1_text)
    await callback.answer()


@router.message(VideoUpload.waiting_for_step1_text, F.text)
async def save_step1_text(message: Message, state: FSMContext):
    """Сохранить текст Шага 1"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text.startswith('/'):
        return
    
    success = await set_setting(FREE_COURSE_STEP1_TEXT_KEY, message.text)
    
    if success:
        preview = message.text[:200] + "..." if len(message.text) > 200 else message.text
        await message.answer(
            f"✅ <b>Текст Шага 1 успешно сохранен!</b>\n\n"
            f"📝 <b>Предпросмотр:</b>\n{preview}",
            reply_markup=get_back_to_free_course_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении</b>\n\nПопробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "free_course_step1_delete")
async def delete_step1_text(callback: CallbackQuery):
    """Удалить текст Шага 1"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = await delete_setting(FREE_COURSE_STEP1_TEXT_KEY)
    
    if success:
        await callback.answer("✅ Текст Шага 1 сброшен")
        from handlers.admin import manage_free_course
        await manage_free_course(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ШАГ 2
@router.callback_query(F.data == "free_course_step2_edit")
async def edit_step2_text(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование текста Шага 2"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    current_text = await get_setting(FREE_COURSE_STEP2_TEXT_KEY)
    
    text = "✏️ <b>Редактирование текста Шага 2 (Программы)</b>\n\n"
    
    if current_text:
        text += f"📝 <b>Текущий текст:</b>\n<code>{current_text[:300]}...</code>\n\n" if len(current_text) > 300 else f"📝 <b>Текущий текст:</b>\n<code>{current_text}</code>\n\n"
    else:
        text += "📝 Сейчас используется стандартный текст\n\n"
    
    text += "Отправьте новый текст для Шага 2\n\n"
    text += "💡 Вы можете использовать эмодзи и форматирование\n"
    text += "Отправьте /cancel для отмены"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_free_course_keyboard())
    await state.set_state(VideoUpload.waiting_for_step2_text)
    await callback.answer()


@router.message(VideoUpload.waiting_for_step2_text, F.text)
async def save_step2_text(message: Message, state: FSMContext):
    """Сохранить текст Шага 2"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text.startswith('/'):
        return
    
    success = await set_setting(FREE_COURSE_STEP2_TEXT_KEY, message.text)
    
    if success:
        preview = message.text[:200] + "..." if len(message.text) > 200 else message.text
        await message.answer(
            f"✅ <b>Текст Шага 2 успешно сохранен!</b>\n\n"
            f"📝 <b>Предпросмотр:</b>\n{preview}",
            reply_markup=get_back_to_free_course_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении</b>\n\nПопробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "free_course_step2_delete")
async def delete_step2_text(callback: CallbackQuery):
    """Удалить текст Шага 2"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = await delete_setting(FREE_COURSE_STEP2_TEXT_KEY)
    
    if success:
        await callback.answer("✅ Текст Шага 2 сброшен")
        from handlers.admin import manage_free_course
        await manage_free_course(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


# ШАГ 3
@router.callback_query(F.data == "free_course_step3_edit")
async def edit_step3_text(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование текста Шага 3"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    current_text = await get_setting(FREE_COURSE_STEP3_TEXT_KEY)
    
    text = "✏️ <b>Редактирование текста Шага 3 (Инструкция Sotis)</b>\n\n"
    
    if current_text:
        text += f"📝 <b>Текущий текст:</b>\n<code>{current_text[:300]}...</code>\n\n" if len(current_text) > 300 else f"📝 <b>Текущий текст:</b>\n<code>{current_text}</code>\n\n"
    else:
        text += "📝 Сейчас используется стандартный текст\n\n"
    
    text += "Отправьте новый текст для Шага 3\n\n"
    text += "💡 Вы можете использовать эмодзи и форматирование\n"
    text += "Отправьте /cancel для отмены"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_free_course_keyboard())
    await state.set_state(VideoUpload.waiting_for_step3_text)
    await callback.answer()


@router.message(VideoUpload.waiting_for_step3_text, F.text)
async def save_step3_text(message: Message, state: FSMContext):
    """Сохранить текст Шага 3"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text.startswith('/'):
        return
    
    success = await set_setting(FREE_COURSE_STEP3_TEXT_KEY, message.text)
    
    if success:
        preview = message.text[:200] + "..." if len(message.text) > 200 else message.text
        await message.answer(
            f"✅ <b>Текст Шага 3 успешно сохранен!</b>\n\n"
            f"📝 <b>Предпросмотр:</b>\n{preview}",
            reply_markup=get_back_to_free_course_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при сохранении</b>\n\nПопробуйте еще раз",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "free_course_step3_delete")
async def delete_step3_text(callback: CallbackQuery):
    """Удалить текст Шага 3"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success = await delete_setting(FREE_COURSE_STEP3_TEXT_KEY)
    
    if success:
        await callback.answer("✅ Текст Шага 3 сброшен")
        from handlers.admin import manage_free_course
        await manage_free_course(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


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


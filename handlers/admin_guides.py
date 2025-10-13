"""
Обработчики для управления гайдами в админ-панели
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func

from config import config
from database import get_db, Guide, Course

router = Router()


class GuideManagement(StatesGroup):
    """Состояния для управления гайдами"""
    creating_name = State()
    creating_guide_id = State()
    creating_emoji = State()
    creating_description = State()
    creating_file_id = State()
    creating_related_course = State()
    editing_name = State()
    editing_emoji = State()
    editing_description = State()
    editing_file_id = State()
    editing_related_course = State()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id == config.ADMIN_ID


# ==================== Список и создание гайдов ====================

@router.callback_query(F.data == "admin_guides")
async def show_guides_management(callback: CallbackQuery):
    """Управление гайдами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db = get_db()
    guides = db.query(Guide).order_by(Guide.order).all()
    
    text = "💝 <b>Управление гайдами</b>\n\n"
    
    if guides:
        for guide in guides:
            status = "✅" if guide.is_active else "❌"
            file_status = "📄" if guide.file_id else "⚠️"
            course_info = f" → {guide.related_course_slug}" if guide.related_course_slug else ""
            text += f"{status} {file_status} {guide.emoji or '💝'} {guide.name}{course_info}\n"
    else:
        text += "Гайды пока не созданы\n"
    
    text += "\n💡 Нажмите на гайд для редактирования"
    
    # Создаём клавиатуру
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем кнопки для каждого гайда
    for guide in guides:
        keyboard.button(
            text=f"{guide.emoji or '💝'} {guide.name}",
            callback_data=f"manage_guide_{guide.id}"
        )
    
    # Кнопка создания нового гайда
    keyboard.button(text="➕ Создать новый гайд", callback_data="create_guide_start")
    keyboard.button(text="🔙 Назад в админ-панель", callback_data="back_to_admin")
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data == "create_guide_start")
async def create_guide_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания нового гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.set_state(GuideManagement.creating_name)
    await callback.message.edit_text(
        "💝 <b>Создание нового гайда</b>\n\n"
        "Шаг 1/6: Введите название гайда:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )
    await callback.answer()


@router.message(GuideManagement.creating_name)
async def create_guide_name(message: Message, state: FSMContext):
    """Сохранение названия и запрос ID"""
    await state.update_data(name=message.text)
    await state.set_state(GuideManagement.creating_guide_id)
    
    await message.answer(
        "💝 <b>Создание нового гайда</b>\n\n"
        f"Название: {message.text}\n\n"
        "Шаг 2/6: Введите уникальный ID гайда (латиница, без пробелов):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )


@router.message(GuideManagement.creating_guide_id)
async def create_guide_id(message: Message, state: FSMContext):
    """Сохранение ID и запрос эмодзи"""
    guide_id = message.text.strip().lower().replace(" ", "-")
    
    # Проверка уникальности ID
    db = get_db()
    existing = db.query(Guide).filter(Guide.guide_id == guide_id).first()
    if existing:
        await message.answer(
            "❌ Гайд с таким ID уже существует. Введите другой ID:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
            ])
        )
        return
    
    await state.update_data(guide_id=guide_id)
    await state.set_state(GuideManagement.creating_emoji)
    
    data = await state.get_data()
    await message.answer(
        "💝 <b>Создание нового гайда</b>\n\n"
        f"Название: {data['name']}\n"
        f"ID: {guide_id}\n\n"
        "Шаг 3/6: Введите эмодзи для гайда (или отправьте '-' чтобы пропустить):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )


@router.message(GuideManagement.creating_emoji)
async def create_guide_emoji(message: Message, state: FSMContext):
    """Сохранение эмодзи и запрос описания"""
    emoji = message.text if message.text != '-' else None
    await state.update_data(emoji=emoji)
    await state.set_state(GuideManagement.creating_description)
    
    data = await state.get_data()
    await message.answer(
        "💝 <b>Создание нового гайда</b>\n\n"
        f"{emoji or '💝'} {data['name']}\n"
        f"ID: {data['guide_id']}\n\n"
        "Шаг 4/6: Введите описание гайда:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )


@router.message(GuideManagement.creating_description)
async def create_guide_description(message: Message, state: FSMContext):
    """Сохранение описания и запрос файла"""
    await state.update_data(description=message.text)
    await state.set_state(GuideManagement.creating_file_id)
    
    data = await state.get_data()
    await message.answer(
        "💝 <b>Создание нового гайда</b>\n\n"
        f"{data.get('emoji') or '💝'} {data['name']}\n\n"
        "Шаг 5/6: Отправьте PDF файл гайда\n"
        "(или отправьте '-' если хотите добавить файл позже):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )


@router.message(GuideManagement.creating_file_id)
async def create_guide_file_id(message: Message, state: FSMContext):
    """Сохранение file_id и запрос связанного курса"""
    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.text and message.text != '-':
        file_id = message.text.strip()
    
    await state.update_data(file_id=file_id)
    await state.set_state(GuideManagement.creating_related_course)
    
    # Получаем список курсов для выбора
    db = get_db()
    courses = db.query(Course).all()
    
    data = await state.get_data()
    text = (
        "💝 <b>Создание нового гайда</b>\n\n"
        f"{data.get('emoji') or '💝'} {data['name']}\n"
        f"Файл: {'✅' if file_id else '❌'}\n\n"
        "Шаг 6/6: Введите slug связанного курса\n"
        "(или отправьте '-' если гайд не связан с курсом)\n\n"
    )
    
    if courses:
        text += "Доступные курсы:\n"
        for course in courses:
            text += f"• {course.slug}\n"
    
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )


@router.message(GuideManagement.creating_related_course)
async def create_guide_save(message: Message, state: FSMContext):
    """Сохранение гайда в БД"""
    related_course = message.text.strip() if message.text != '-' else None
    
    data = await state.get_data()
    db = get_db()
    
    try:
        # Определяем максимальный order
        max_order = db.query(func.max(Guide.order)).scalar() or 0
        
        # Создаём новый гайд
        new_guide = Guide(
            guide_id=data['guide_id'],
            name=data['name'],
            emoji=data.get('emoji'),
            description=data['description'],
            file_id=data.get('file_id'),
            related_course_slug=related_course,
            order=max_order + 1,
            is_active=True
        )
        
        db.add(new_guide)
        db.commit()
        
        text = (
            "✅ <b>Гайд успешно создан!</b>\n\n"
            f"{new_guide.emoji or '💝'} {new_guide.name}\n"
            f"ID: {new_guide.guide_id}\n"
            f"Файл: {'✅' if new_guide.file_id else '❌'}\n"
            f"Связан с курсом: {related_course or '-'}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К списку гайдов", callback_data="admin_guides")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании гайда: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К списку гайдов", callback_data="admin_guides")]
            ])
        )
    finally:
        db.close()
        await state.clear()


# ==================== Управление гайдом ====================

@router.callback_query(F.data.startswith("manage_guide_"))
async def manage_guide(callback: CallbackQuery):
    """Управление конкретным гайдом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = int(callback.data.split("_")[2])
    db = get_db()
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    
    if not guide:
        await callback.answer("❌ Гайд не найден", show_alert=True)
        return
    
    status_text = "Активен ✅" if guide.is_active else "Неактивен ❌"
    file_text = "Загружен ✅" if guide.file_id else "Не загружен ❌"
    course_text = guide.related_course_slug or "Не указан"
    
    text = (
        f"💝 <b>{guide.name}</b>\n\n"
        f"ID: <code>{guide.guide_id}</code>\n"
        f"Эмодзи: {guide.emoji or '-'}\n"
        f"Описание: {guide.description or '-'}\n"
        f"Файл: {file_text}\n"
        f"Связан с курсом: {course_text}\n"
        f"Статус: {status_text}\n"
        f"Порядок: {guide.order}"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Название", callback_data=f"edit_guide_name_{guide_id}")
    keyboard.button(text="🎨 Эмодзи", callback_data=f"edit_guide_emoji_{guide_id}")
    keyboard.button(text="📝 Описание", callback_data=f"edit_guide_desc_{guide_id}")
    keyboard.button(text="📄 Файл", callback_data=f"edit_guide_file_{guide_id}")
    keyboard.button(text="🔗 Связь с курсом", callback_data=f"edit_guide_course_{guide_id}")
    
    toggle_text = "🔴 Деактивировать" if guide.is_active else "🟢 Активировать"
    keyboard.button(text=toggle_text, callback_data=f"toggle_guide_{guide_id}")
    
    keyboard.button(text="🗑 Удалить гайд", callback_data=f"delete_guide_confirm_{guide_id}")
    keyboard.button(text="🔙 К списку гайдов", callback_data="admin_guides")
    keyboard.adjust(2, 2, 1, 1, 1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_guide_"))
async def toggle_guide(callback: CallbackQuery):
    """Переключение активности гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = int(callback.data.split("_")[2])
    db = get_db()
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    
    if guide:
        guide.is_active = not guide.is_active
        db.commit()
        await callback.answer(
            f"✅ Гайд {'активирован' if guide.is_active else 'деактивирован'}",
            show_alert=True
        )
        # Обновляем сообщение
        await manage_guide(callback)
    else:
        await callback.answer("❌ Гайд не найден", show_alert=True)
    
    db.close()


@router.callback_query(F.data.startswith("delete_guide_confirm_"))
async def delete_guide_confirm(callback: CallbackQuery):
    """Подтверждение удаления гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = int(callback.data.split("_")[3])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_guide_{guide_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_guide_{guide_id}")
        ]
    ])
    
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены, что хотите удалить этот гайд?</b>\n\n"
        "Это действие нельзя отменить!",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_guide_"))
async def delete_guide(callback: CallbackQuery):
    """Удаление гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = int(callback.data.split("_")[2])
    db = get_db()
    
    try:
        guide = db.query(Guide).filter(Guide.id == guide_id).first()
        if guide:
            guide_name = guide.name
            db.delete(guide)
            db.commit()
            await callback.answer(f"✅ Гайд '{guide_name}' удален", show_alert=True)
            await show_guides_management(callback)
        else:
            await callback.answer("❌ Гайд не найден", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    finally:
        db.close()


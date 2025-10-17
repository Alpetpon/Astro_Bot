"""
Обработчики для управления гайдами в админ-панели (JSON)
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re

from config import config
from data import (
    get_all_guides,
    get_guide_by_id,
    get_all_courses,
    save_guide,
    delete_guide
)
from utils.bot_settings import is_admin

router = Router()


def transliterate(text: str) -> str:
    """Транслитерация русского текста в латиницу для ID"""
    translit_dict = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    
    text = text.lower()
    result = ''
    for char in text:
        if char in translit_dict:
            result += translit_dict[char]
        elif char.isalnum() or char in '-_':
            result += char
        elif char.isspace():
            result += '-'
    
    # Убираем повторяющиеся дефисы и дефисы в начале/конце
    result = re.sub(r'-+', '-', result)
    result = result.strip('-')
    
    return result


class GuideManagement(StatesGroup):
    """Состояния для управления гайдами"""
    creating_name = State()
    creating_emoji = State()
    creating_description = State()
    creating_file_id = State()
    creating_related_course = State()
    editing_name = State()
    editing_emoji = State()
    editing_description = State()
    editing_file_id = State()
    editing_related_course = State()


# ==================== Список и создание гайдов ====================

@router.callback_query(F.data == "admin_guides")
async def show_guides_management(callback: CallbackQuery):
    """Управление гайдами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guides = get_all_guides()
    
    text = f"💝 <b>Управление гайдами</b>\n\n"
    text += f"📊 Всего гайдов: {len(guides)}\n\n"
    
    if guides:
        for guide in guides:
            status = "✅" if guide.get('is_active', True) else "❌"
            file_status = "📄" if guide.get('file_id') else "⚠️"
            course_info = f" → {guide.get('related_course_slug', '')}" if guide.get('related_course_slug') else ""
            text += f"{status} {file_status} {guide.get('emoji', '💝')} {guide['name']}{course_info}\n"
    else:
        text += "Гайды пока не созданы\n"
    
    text += "\n💡 Нажмите на гайд для редактирования"
    
    # Создаём клавиатуру
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем кнопки для каждого гайда
    for guide in guides:
        keyboard.button(
            text=f"{guide.get('emoji', '💝')} {guide['name']}",
            callback_data=f"manage_guide_{guide['id']}"
        )
    
    # Кнопка создания нового гайда
    keyboard.button(text="➕ Создать новый гайд", callback_data="create_guide_start")
    keyboard.button(text="🔙 Назад в админ-панель", callback_data="admin_panel")
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
        "Шаг 1/5: Введите название гайда:\n\n"
        "💡 ID будет сгенерирован автоматически из названия",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )
    await callback.answer()


@router.message(GuideManagement.creating_name)
async def create_guide_name(message: Message, state: FSMContext):
    """Сохранение названия, генерация ID и запрос эмодзи"""
    name = message.text
    guide_id = transliterate(name)
    
    # Проверка уникальности ID
    counter = 1
    original_id = guide_id
    while get_guide_by_id(guide_id):
        guide_id = f"{original_id}-{counter}"
        counter += 1
    
    await state.update_data(name=name, guide_id=guide_id)
    await state.set_state(GuideManagement.creating_emoji)
    
    await message.answer(
        "💝 <b>Создание нового гайда</b>\n\n"
        f"Название: {name}\n"
        f"ID: <code>{guide_id}</code>\n\n"
        "Шаг 2/5: Введите эмодзи для гайда (или отправьте '-' чтобы пропустить):",
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
        f"ID: <code>{data['guide_id']}</code>\n\n"
        "Шаг 3/5: Введите описание гайда:",
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
        "Шаг 4/5: Отправьте PDF файл гайда\n"
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
    courses = get_all_courses()
    
    data = await state.get_data()
    text = (
        "💝 <b>Создание нового гайда</b>\n\n"
        f"{data.get('emoji') or '💝'} {data['name']}\n"
        f"Файл: {'✅' if file_id else '❌'}\n\n"
        "Шаг 5/5: Введите slug связанного курса\n"
        "(или отправьте '-' если гайд не связан с курсом)\n\n"
    )
    
    if courses:
        text += "Доступные курсы:\n"
        for course in courses:
            text += f"• {course['slug']}\n"
    
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_guides")]
        ])
    )


@router.message(GuideManagement.creating_related_course)
async def create_guide_save(message: Message, state: FSMContext):
    """Сохранение гайда в JSON"""
    related_course = message.text.strip() if message.text != '-' else None
    
    data = await state.get_data()
    
    try:
        # Определяем максимальный order
        guides = get_all_guides()
        max_order = max([g.get('order', 0) for g in guides], default=0)
        
        # Создаём новый гайд
        new_guide = {
            'id': data['guide_id'],
            'name': data['name'],
            'emoji': data.get('emoji'),
            'description': data['description'],
            'file_id': data.get('file_id'),
            'related_course_slug': related_course,
            'order': max_order + 1,
            'is_active': True
        }
        
        save_guide(new_guide)
        
        text = (
            "✅ <b>Гайд успешно создан и сохранен в JSON!</b>\n\n"
            f"{new_guide['emoji'] or '💝'} {new_guide['name']}\n"
            f"ID: {new_guide['id']}\n"
            f"Файл: {'✅' if new_guide['file_id'] else '❌'}\n"
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
        await state.clear()


# ==================== Управление гайдом ====================

@router.callback_query(F.data.startswith("manage_guide_"))
async def manage_guide(callback: CallbackQuery):
    """Управление конкретным гайдом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[2]
    guide = get_guide_by_id(guide_id)
    
    if not guide:
        await callback.answer("❌ Гайд не найден", show_alert=True)
        return
    
    status_text = "Активен ✅" if guide.get('is_active', True) else "Неактивен ❌"
    file_text = "Загружен ✅" if guide.get('file_id') else "Не загружен ❌"
    course_text = guide.get('related_course_slug') or "Не указан"
    
    text = (
        f"💝 <b>{guide['name']}</b>\n\n"
        f"ID: <code>{guide['id']}</code>\n"
        f"Эмодзи: {guide.get('emoji') or '-'}\n"
        f"Описание: {guide.get('description') or '-'}\n"
        f"Файл: {file_text}\n"
        f"Связан с курсом: {course_text}\n"
        f"Статус: {status_text}\n"
        f"Порядок: {guide.get('order', 0)}"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Название", callback_data=f"edit_guide_name_{guide_id}")
    keyboard.button(text="🎨 Эмодзи", callback_data=f"edit_guide_emoji_{guide_id}")
    keyboard.button(text="📝 Описание", callback_data=f"edit_guide_desc_{guide_id}")
    keyboard.button(text="📄 Файл", callback_data=f"edit_guide_file_{guide_id}")
    keyboard.button(text="🔗 Связь с курсом", callback_data=f"edit_guide_course_{guide_id}")
    
    toggle_text = "🔴 Деактивировать" if guide.get('is_active', True) else "🟢 Активировать"
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
    
    guide_id = callback.data.split("_")[2]
    guide = get_guide_by_id(guide_id)
    
    if guide:
        guide['is_active'] = not guide.get('is_active', True)
        save_guide(guide)
        
        await callback.answer(
            f"✅ Гайд {'активирован' if guide['is_active'] else 'деактивирован'}",
            show_alert=True
        )
        # Обновляем сообщение
        await manage_guide(callback)
    else:
        await callback.answer("❌ Гайд не найден", show_alert=True)


@router.callback_query(F.data.startswith("delete_guide_confirm_"))
async def delete_guide_confirm(callback: CallbackQuery):
    """Подтверждение удаления гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[3]
    
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
async def delete_guide_handler(callback: CallbackQuery):
    """Удаление гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[2]
    guide = get_guide_by_id(guide_id)
    
    if guide:
        guide_name = guide['name']
        if delete_guide(guide_id):
            await callback.answer(f"✅ Гайд '{guide_name}' удален", show_alert=True)
            await show_guides_management(callback)
        else:
            await callback.answer("❌ Ошибка при удалении", show_alert=True)
    else:
        await callback.answer("❌ Гайд не найден", show_alert=True)


# ==================== Редактирование гайда ====================

@router.callback_query(F.data.startswith("edit_guide_name_"))
async def edit_guide_name_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[3]
    guide = get_guide_by_id(guide_id)
    
    if not guide:
        await callback.answer("❌ Гайд не найден", show_alert=True)
        return
    
    await state.update_data(editing_guide_id=guide_id)
    await state.set_state(GuideManagement.editing_name)
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование названия гайда</b>\n\n"
        f"Текущее название: {guide['name']}\n\n"
        f"Введите новое название:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_guide_{guide_id}")]
        ])
    )
    await callback.answer()


@router.message(GuideManagement.editing_name)
async def edit_guide_name_save(message: Message, state: FSMContext):
    """Сохранение нового названия гайда"""
    data = await state.get_data()
    guide_id = data.get('editing_guide_id')
    
    guide = get_guide_by_id(guide_id)
    
    if guide:
        guide['name'] = message.text
        save_guide(guide)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К гайду", callback_data=f"manage_guide_{guide_id}")]
        ])
        
        await message.answer(
            f"✅ Название обновлено!\n\nНовое название: {message.text}",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Гайд не найден")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_guide_emoji_"))
async def edit_guide_emoji_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования эмодзи гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[3]
    guide = get_guide_by_id(guide_id)
    
    if not guide:
        await callback.answer("❌ Гайд не найден", show_alert=True)
        return
    
    await state.update_data(editing_guide_id=guide_id)
    await state.set_state(GuideManagement.editing_emoji)
    
    await callback.message.edit_text(
        f"🎨 <b>Редактирование эмодзи гайда</b>\n\n"
        f"Текущий эмодзи: {guide.get('emoji') or '-'}\n\n"
        f"Введите новый эмодзи (или отправьте '-' чтобы удалить):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_guide_{guide_id}")]
        ])
    )
    await callback.answer()


@router.message(GuideManagement.editing_emoji)
async def edit_guide_emoji_save(message: Message, state: FSMContext):
    """Сохранение нового эмодзи гайда"""
    data = await state.get_data()
    guide_id = data.get('editing_guide_id')
    
    guide = get_guide_by_id(guide_id)
    
    if guide:
        guide['emoji'] = message.text if message.text != '-' else None
        save_guide(guide)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К гайду", callback_data=f"manage_guide_{guide_id}")]
        ])
        
        await message.answer(
            f"✅ Эмодзи обновлен!\n\nНовый эмодзи: {guide['emoji'] or '-'}",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Гайд не найден")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_guide_desc_"))
async def edit_guide_desc_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования описания гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[3]
    guide = get_guide_by_id(guide_id)
    
    if not guide:
        await callback.answer("❌ Гайд не найден", show_alert=True)
        return
    
    await state.update_data(editing_guide_id=guide_id)
    await state.set_state(GuideManagement.editing_description)
    
    await callback.message.edit_text(
        f"📝 <b>Редактирование описания гайда</b>\n\n"
        f"Текущее описание:\n{guide.get('description') or '-'}\n\n"
        f"Введите новое описание:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_guide_{guide_id}")]
        ])
    )
    await callback.answer()


@router.message(GuideManagement.editing_description)
async def edit_guide_desc_save(message: Message, state: FSMContext):
    """Сохранение нового описания гайда"""
    data = await state.get_data()
    guide_id = data.get('editing_guide_id')
    
    guide = get_guide_by_id(guide_id)
    
    if guide:
        guide['description'] = message.text
        save_guide(guide)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К гайду", callback_data=f"manage_guide_{guide_id}")]
        ])
        
        await message.answer(
            f"✅ Описание обновлено!",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Гайд не найден")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_guide_file_"))
async def edit_guide_file_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования файла гайда"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[3]
    guide = get_guide_by_id(guide_id)
    
    if not guide:
        await callback.answer("❌ Гайд не найден", show_alert=True)
        return
    
    await state.update_data(editing_guide_id=guide_id)
    await state.set_state(GuideManagement.editing_file_id)
    
    file_status = "Загружен ✅" if guide.get('file_id') else "Не загружен ❌"
    
    await callback.message.edit_text(
        f"📄 <b>Редактирование файла гайда</b>\n\n"
        f"Текущий файл: {file_status}\n\n"
        f"Отправьте новый PDF файл или file_id\n"
        f"(или отправьте '-' чтобы удалить файл):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_guide_{guide_id}")]
        ])
    )
    await callback.answer()


@router.message(GuideManagement.editing_file_id)
async def edit_guide_file_save(message: Message, state: FSMContext):
    """Сохранение нового файла гайда"""
    data = await state.get_data()
    guide_id = data.get('editing_guide_id')
    
    guide = get_guide_by_id(guide_id)
    
    if guide:
        if message.document:
            guide['file_id'] = message.document.file_id
        elif message.text and message.text != '-':
            guide['file_id'] = message.text.strip()
        else:
            guide['file_id'] = None
        
        save_guide(guide)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К гайду", callback_data=f"manage_guide_{guide_id}")]
        ])
        
        file_status = "загружен ✅" if guide.get('file_id') else "удален ❌"
        await message.answer(
            f"✅ Файл {file_status}!",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Гайд не найден")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_guide_course_"))
async def edit_guide_course_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования связи с курсом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    guide_id = callback.data.split("_")[3]
    guide = get_guide_by_id(guide_id)
    
    if not guide:
        await callback.answer("❌ Гайд не найден", show_alert=True)
        return
    
    # Получаем список курсов
    courses = get_all_courses()
    
    await state.update_data(editing_guide_id=guide_id)
    await state.set_state(GuideManagement.editing_related_course)
    
    text = (
        f"🔗 <b>Редактирование связи с курсом</b>\n\n"
        f"Текущий курс: {guide.get('related_course_slug') or '-'}\n\n"
        f"Введите slug курса (или '-' чтобы удалить связь)\n\n"
    )
    
    if courses:
        text += "Доступные курсы:\n"
        for course in courses:
            text += f"• {course['slug']}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_guide_{guide_id}")]
        ])
    )
    await callback.answer()


@router.message(GuideManagement.editing_related_course)
async def edit_guide_course_save(message: Message, state: FSMContext):
    """Сохранение новой связи с курсом"""
    data = await state.get_data()
    guide_id = data.get('editing_guide_id')
    
    guide = get_guide_by_id(guide_id)
    
    if guide:
        guide['related_course_slug'] = message.text.strip() if message.text != '-' else None
        save_guide(guide)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К гайду", callback_data=f"manage_guide_{guide_id}")]
        ])
        
        await message.answer(
            f"✅ Связь с курсом обновлена!\n\nКурс: {guide.get('related_course_slug') or '-'}",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Гайд не найден")
    
    await state.clear()

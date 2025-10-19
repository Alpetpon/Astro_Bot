from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

from data import get_mini_course, save_mini_course
from utils.bot_settings import is_admin
from keyboards import get_bot_management_keyboard

router = Router()


@router.callback_query(F.data == "admin_bot_management")
async def show_bot_management(callback: CallbackQuery, state: FSMContext):
    """Показать меню управления ботом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Сбрасываем состояние при выходе из редактирования
    await state.clear()
    
    await callback.message.edit_text(
        "🤖 <b>Управление ботом</b>\n\n"
        "Выберите раздел для настройки:",
        reply_markup=get_bot_management_keyboard()
    )
    await callback.answer()


class MiniCourseEdit(StatesGroup):
    """Состояния для редактирования мини-курса"""
    editing_title = State()
    editing_subtitle = State()
    editing_start_date = State()
    editing_description = State()
    editing_format = State()
    editing_summary = State()
    editing_registration_text = State()
    editing_tariff_price = State()


def get_mini_course_admin_keyboard(is_active: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура управления мини-курсом"""
    status_text = "✅ Выключить" if is_active else "❌ Включить"
    status_callback = "mini_course_toggle_off" if is_active else "mini_course_toggle_on"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить заголовок", callback_data="mini_course_edit_title")],
        [InlineKeyboardButton(text="📅 Изменить дату старта", callback_data="mini_course_edit_date")],
        [InlineKeyboardButton(text="📄 Изменить описание", callback_data="mini_course_edit_description")],
        [InlineKeyboardButton(text="📚 Изменить формат обучения", callback_data="mini_course_edit_format")],
        [InlineKeyboardButton(text="💰 Редактировать тарифы", callback_data="mini_course_edit_tariffs")],
        [InlineKeyboardButton(text=status_text, callback_data=status_callback)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bot_management")]
    ])
    return keyboard


def get_tariffs_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура редактирования тарифов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Тариф 'Самостоятельное'", callback_data="mini_course_tariff_solo")],
        [InlineKeyboardButton(text="👨‍🏫 Тариф 'С сопровождением'", callback_data="mini_course_tariff_support")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_mini_course")]
    ])
    return keyboard


def get_tariff_edit_keyboard(tariff_id: str) -> InlineKeyboardMarkup:
    """Клавиатура редактирования конкретного тарифа"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"mini_course_price_{tariff_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="mini_course_edit_tariffs")]
    ])
    return keyboard


@router.callback_query(F.data == "admin_mini_course")
async def show_mini_course_admin(callback: CallbackQuery):
    """Показать панель управления мини-курсом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    mini_course = get_mini_course()
    
    if not mini_course:
        await callback.message.edit_text(
            "❌ Мини-курс не найден в данных",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bot_management")]
            ])
        )
        return
    
    is_active = mini_course.get('is_active', False)
    status_emoji = "✅" if is_active else "❌"
    
    text = f"🌌 <b>Управление мини-курсом</b>\n\n"
    text += f"<b>Статус:</b> {status_emoji} {'Активен' if is_active else 'Неактивен'}\n\n"
    text += f"<b>Заголовок:</b> {mini_course.get('title', 'Не указан')}\n"
    text += f"<b>Подзаголовок:</b> {mini_course.get('subtitle', 'Не указан')}\n"
    text += f"<b>Дата старта:</b> {mini_course.get('start_date', 'Не указана')}\n\n"
    
    # Тарифы
    text += "<b>Тарифы:</b>\n"
    for tariff in mini_course.get('tariffs', []):
        text += f"  {tariff['emoji']} {tariff['name']} - {tariff['price']} ₽\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_mini_course_admin_keyboard(is_active)
    )
    await callback.answer()


@router.callback_query(F.data.in_(["mini_course_toggle_on", "mini_course_toggle_off"]))
async def toggle_mini_course(callback: CallbackQuery):
    """Включить/выключить мини-курс"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    mini_course = get_mini_course()
    if not mini_course:
        await callback.answer("❌ Мини-курс не найден", show_alert=True)
        return
    
    # Переключаем статус
    new_status = callback.data == "mini_course_toggle_on"
    mini_course['is_active'] = new_status
    save_mini_course(mini_course)
    
    status_text = "включен" if new_status else "выключен"
    await callback.answer(f"✅ Мини-курс {status_text}")
    
    # Обновляем сообщение
    await show_mini_course_admin(callback)


@router.callback_query(F.data == "mini_course_edit_title")
async def start_edit_title(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование заголовка"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(MiniCourseEdit.editing_title)
    await callback.message.edit_text(
        "📝 Отправьте новый заголовок мини-курса:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_mini_course")]
        ])
    )
    await callback.answer()


@router.message(StateFilter(MiniCourseEdit.editing_title))
async def save_title(message: Message, state: FSMContext):
    """Сохранить новый заголовок"""
    if not is_admin(message.from_user.id):
        return
    
    mini_course = get_mini_course()
    if not mini_course:
        await message.answer("❌ Мини-курс не найден")
        await state.clear()
        return
    
    mini_course['title'] = message.text
    save_mini_course(mini_course)
    
    await message.answer("✅ Заголовок обновлен!")
    await state.clear()
    
    # Показываем обновленную админ-панель
    is_active = mini_course.get('is_active', False)
    status_emoji = "✅" if is_active else "❌"
    
    text = f"🌌 <b>Управление мини-курсом</b>\n\n"
    text += f"<b>Статус:</b> {status_emoji} {'Активен' if is_active else 'Неактивен'}\n\n"
    text += f"<b>Заголовок:</b> {mini_course.get('title', 'Не указан')}\n"
    text += f"<b>Подзаголовок:</b> {mini_course.get('subtitle', 'Не указан')}\n"
    text += f"<b>Дата старта:</b> {mini_course.get('start_date', 'Не указана')}\n\n"
    
    text += "<b>Тарифы:</b>\n"
    for tariff in mini_course.get('tariffs', []):
        text += f"  {tariff['emoji']} {tariff['name']} - {tariff['price']} ₽\n"
    
    await message.answer(
        text,
        reply_markup=get_mini_course_admin_keyboard(is_active)
    )


@router.callback_query(F.data == "mini_course_edit_date")
async def start_edit_date(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование даты старта"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(MiniCourseEdit.editing_start_date)
    await callback.message.edit_text(
        "📅 Отправьте новую дату старта (например: 13 октября):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_mini_course")]
        ])
    )
    await callback.answer()


@router.message(StateFilter(MiniCourseEdit.editing_start_date))
async def save_date(message: Message, state: FSMContext):
    """Сохранить новую дату старта"""
    if not is_admin(message.from_user.id):
        return
    
    mini_course = get_mini_course()
    if not mini_course:
        await message.answer("❌ Мини-курс не найден")
        await state.clear()
        return
    
    mini_course['start_date'] = message.text
    save_mini_course(mini_course)
    
    await message.answer("✅ Дата старта обновлена!")
    await state.clear()
    
    # Показываем обновленную админ-панель
    is_active = mini_course.get('is_active', False)
    status_emoji = "✅" if is_active else "❌"
    
    text = f"🌌 <b>Управление мини-курсом</b>\n\n"
    text += f"<b>Статус:</b> {status_emoji} {'Активен' if is_active else 'Неактивен'}\n\n"
    text += f"<b>Заголовок:</b> {mini_course.get('title', 'Не указан')}\n"
    text += f"<b>Подзаголовок:</b> {mini_course.get('subtitle', 'Не указан')}\n"
    text += f"<b>Дата старта:</b> {mini_course.get('start_date', 'Не указана')}\n\n"
    
    text += "<b>Тарифы:</b>\n"
    for tariff in mini_course.get('tariffs', []):
        text += f"  {tariff['emoji']} {tariff['name']} - {tariff['price']} ₽\n"
    
    await message.answer(
        text,
        reply_markup=get_mini_course_admin_keyboard(is_active)
    )


@router.callback_query(F.data == "mini_course_edit_tariffs")
async def show_tariffs_admin(callback: CallbackQuery):
    """Показать список тарифов для редактирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    mini_course = get_mini_course()
    if not mini_course:
        await callback.answer("❌ Мини-курс не найден", show_alert=True)
        return
    
    text = "💰 <b>Редактирование тарифов</b>\n\n"
    for tariff in mini_course.get('tariffs', []):
        text += f"{tariff['emoji']} <b>{tariff['name']}</b>\n"
        text += f"Цена: {tariff['price']} ₽\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_tariffs_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.in_(["mini_course_tariff_solo", "mini_course_tariff_support"]))
async def show_tariff_edit(callback: CallbackQuery):
    """Показать редактирование конкретного тарифа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    tariff_id = "mini-solo" if callback.data == "mini_course_tariff_solo" else "mini-support"
    
    mini_course = get_mini_course()
    if not mini_course:
        await callback.answer("❌ Мини-курс не найден", show_alert=True)
        return
    
    # Находим тариф
    tariff = None
    for t in mini_course.get('tariffs', []):
        if t['id'] == tariff_id:
            tariff = t
            break
    
    if not tariff:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    text = f"{tariff['emoji']} <b>{tariff['name']}</b>\n\n"
    text += f"<b>Текущая цена:</b> {tariff['price']} ₽\n\n"
    text += "<b>Что входит:</b>\n"
    for feature in tariff.get('features', []):
        text += f"✔️ {feature}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_tariff_edit_keyboard(tariff_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mini_course_price_"))
async def start_edit_price(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование цены тарифа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    tariff_id = callback.data.replace("mini_course_price_", "")
    await state.update_data(tariff_id=tariff_id)
    await state.set_state(MiniCourseEdit.editing_tariff_price)
    
    await callback.message.edit_text(
        "💰 Отправьте новую цену (только число, без знака рубля):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="mini_course_edit_tariffs")]
        ])
    )
    await callback.answer()


@router.message(StateFilter(MiniCourseEdit.editing_tariff_price))
async def save_price(message: Message, state: FSMContext):
    """Сохранить новую цену тарифа"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        new_price = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (например: 5000)")
        return
    
    data = await state.get_data()
    tariff_id = data.get('tariff_id')
    
    mini_course = get_mini_course()
    if not mini_course:
        await message.answer("❌ Мини-курс не найден")
        await state.clear()
        return
    
    # Обновляем цену
    updated = False
    for tariff in mini_course.get('tariffs', []):
        if tariff['id'] == tariff_id:
            tariff['price'] = new_price
            updated = True
            break
    
    if not updated:
        await message.answer("❌ Тариф не найден")
        await state.clear()
        return
    
    save_mini_course(mini_course)
    await message.answer(f"✅ Цена обновлена на {new_price} ₽!")
    await state.clear()
    
    # Показываем список тарифов
    text = "💰 <b>Редактирование тарифов</b>\n\n"
    for tariff in mini_course.get('tariffs', []):
        text += f"{tariff['emoji']} <b>{tariff['name']}</b>\n"
        text += f"Цена: {tariff['price']} ₽\n\n"
    
    await message.answer(
        text,
        reply_markup=get_tariffs_admin_keyboard()
    )


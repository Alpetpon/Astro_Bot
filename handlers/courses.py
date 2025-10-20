from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from database import get_db, UserRepository
from data import get_active_courses, get_course_by_slug, get_tariff_by_id
from keyboards import (
    get_courses_keyboard,
    get_course_detail_keyboard,
    get_back_keyboard
)

router = Router()


@router.callback_query(F.data == "courses")
async def show_courses_catalog(callback: CallbackQuery):
    """Показать каталог курсов"""
    # Обновляем активность пользователя
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Получаем активные курсы из JSON
    courses = get_active_courses()
    
    if not courses:
        text = "📚 К сожалению, сейчас нет доступных курсов."
        markup = get_back_keyboard("main_menu")
    else:
        text = "📚 **Каталог курсов**\n\nВыберите интересующий вас курс:"
        markup = get_courses_keyboard(courses)
    
    try:
        # Если это видео - удаляем и отправляем новое сообщение
        if callback.message.video:
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            # Если текст - редактируем
            await callback.message.edit_text(
                text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except Exception:
        # Если не можем отредактировать - удаляем и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("course_register_"))
async def show_tariff_selection(callback: CallbackQuery):
    """Показать выбор тарифа для записи - перенаправление на стоимость"""
    course_slug = callback.data.replace("course_register_", "")
    
    # Создаем mock callback с нужным data
    class CallbackDataWrapper:
        def __init__(self, original_callback, new_data):
            self._original = original_callback
            self.data = new_data
            
        def __getattr__(self, name):
            return getattr(self._original, name)
    
    # Перенаправляем на обработчик стоимости
    wrapped_callback = CallbackDataWrapper(callback, f"course_price_{course_slug}")
    await show_course_price(wrapped_callback)


@router.callback_query(F.data.startswith("course_price_"))
async def show_course_price(callback: CallbackQuery):
    """Показать тарифы курса для выбора"""
    course_slug = callback.data.replace("course_price_", "")
    
    # Получаем курс из JSON
    course = get_course_by_slug(course_slug)
    
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    
    tariffs = course.get('tariffs', [])
    active_tariffs = [t for t in tariffs if t.get('is_active', True)]
    
    if not active_tariffs:
        await callback.answer("Тарифы не найдены", show_alert=True)
        return
    
    # Формируем текст с описанием тарифов
    emoji = course.get('emoji', '📚')
    text = f"💰 **Стоимость курса «{course['name']}»**\n\n"
    
    # Добавляем информацию о каждом тарифе
    for tariff in active_tariffs:
        support_text = "✅ С сопровождением" if tariff.get('with_support') else "📚 Самостоятельно"
        text += f"**{tariff['name']}** — {tariff['price']} ₽\n"
        text += f"{support_text}\n"
        if tariff.get('description'):
            text += f"{tariff['description']}\n"
        
        text += "\nЧто входит:\n"
        if tariff.get('features'):
            for feature in tariff['features']:
                text += f"✔️ {feature}\n"
        
        text += "\n"
    
    text += "Выберите подходящий вам вариант обучения:"
    
    # Создаем кнопки с тарифами
    buttons = []
    for tariff in active_tariffs:
        support_emoji = "👨‍🏫" if tariff.get('with_support') else "📚"
        buttons.append([InlineKeyboardButton(
            text=f"{support_emoji} {tariff['name']} — {tariff['price']} ₽",
            callback_data=f"tariff_{course_slug}_{tariff['id']}"
        )])
    
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("course_"))
async def show_course_detail(callback: CallbackQuery):
    """Показать детальную информацию о курсе - вся информация в одном сообщении"""
    # Извлекаем slug курса
    parts = callback.data.split("_")
    
    if len(parts) < 2:
        await callback.answer("Ошибка при загрузке курса", show_alert=True)
        return
    
    course_slug = "_".join(parts[1:])
    
    # Получаем курс из JSON
    course = get_course_by_slug(course_slug)
    
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    
    # Показываем полную информацию о курсе
    emoji = course.get('emoji', '📚')
    text = f"{emoji} **{course['name']}**\n\n"
    text += f"{course.get('description', '')}\n\n"
    
    if course.get('duration'):
        text += f"⏱ **Длительность:** {course['duration']}\n\n"
    
    if course.get('program'):
        text += "📋 **Программа:**\n"
        for module in course['program']:
            text += f"• {module}\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_course_detail_keyboard(course_slug),
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать (например, это документ, видео или фото)
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_course_detail_keyboard(course_slug),
            parse_mode="Markdown"
        )
    
    await callback.answer()

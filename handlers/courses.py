from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database import get_db, UserRepository
from data import get_active_courses, get_course_by_slug, get_tariff_by_id
from keyboards import (
    get_courses_keyboard,
    get_course_detail_keyboard,
    get_tariff_keyboard,
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
        await callback.message.edit_text(
            text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать
        if callback.message.video:
            # Если видео - НЕ удаляем
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            # Если фото - удаляем и отправляем новое
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
    """Показать выбор тарифа для записи"""
    course_slug = callback.data.replace("course_register_", "")
    
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
    
    text = f"📝 **Выберите тариф**\n\n"
    text += f"Курс: {course['name']}\n\n"
    text += "Выберите подходящий вам вариант обучения:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_tariff_keyboard(course_slug, active_tariffs),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("course_"))
async def show_course_detail(callback: CallbackQuery):
    """Показать детальную информацию о курсе"""
    # Извлекаем slug курса
    parts = callback.data.split("_")
    
    if len(parts) < 2:
        await callback.answer("Ошибка при загрузке курса", show_alert=True)
        return
    
    # Проверяем, это навигация или просмотр курса
    if parts[1] == "about":
        course_slug = "_".join(parts[2:])
        show_about = True
    elif parts[1] == "price":
        course_slug = "_".join(parts[2:])
        show_about = False
    else:
        course_slug = "_".join(parts[1:])
        show_about = True
    
    # Получаем курс из JSON
    course = get_course_by_slug(course_slug)
    
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    
    if show_about:
        # Показываем информацию о курсе
        emoji = course.get('emoji', '📚')
        text = f"{emoji} **{course['name']}**\n\n"
        text += f"{course.get('description', '')}\n\n"
        
        if course.get('duration'):
            text += f"⏱ **Длительность:** {course['duration']}\n\n"
        
        if course.get('program'):
            text += "📋 **Программа:**\n"
            for module in course['program']:
                text += f"• {module}\n"
    else:
        # Показываем тарифы
        emoji = course.get('emoji', '📚')
        text = f"💰 **Тарифы курса «{course['name']}»**\n\n"
        
        tariffs = course.get('tariffs', [])
        active_tariffs = [t for t in tariffs if t.get('is_active', True)]
        
        for tariff in active_tariffs:
            support_text = "✅ С сопровождением" if tariff.get('with_support') else "📚 Самостоятельно"
            text += f"**{tariff['name']}** - {tariff['price']} ₽\n"
            text += f"{support_text}\n"
            text += f"{tariff.get('description', '')}\n"
            
            if tariff.get('features'):
                for feature in tariff['features']:
                    text += f"  • {feature}\n"
            
            text += "\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_course_detail_keyboard(course_slug),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        # Сообщение не изменилось - это нормально
        pass
    
    await callback.answer()

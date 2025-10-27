from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database import get_db, UserRepository
from data import get_active_consultations, get_consultation_by_slug, get_consultation_option
from keyboards import (
    get_consultations_keyboard,
    get_consultation_detail_keyboard,
    get_consultation_options_keyboard,
    get_back_keyboard
)

router = Router()


@router.callback_query(F.data == "consultations")
async def show_consultations_catalog(callback: CallbackQuery):
    """Показать каталог консультаций"""
    db = await get_db()
    user_repo = UserRepository(db)
    
    # Обновляем активность
    await user_repo.update_activity(callback.from_user.id)
    
    # Получаем активные консультации из JSON
    consultations = get_active_consultations()
    
    if not consultations:
        text = "🔮 К сожалению, сейчас нет доступных консультаций."
        markup = get_back_keyboard("main_menu")
    else:
        text = "🔮 **Консультационные услуги**\n\n"
        text += "Выберите интересующую вас услугу для получения подробной информации:"
        markup = get_consultations_keyboard(consultations)
    
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


# Этот обработчик больше не нужен - запись идет через Telegram
# @router.callback_query(F.data.startswith("consultation_book_"))
# async def show_consultation_booking(callback: CallbackQuery):
#     """Показать варианты консультации для записи"""
#     # Теперь кнопка "Записаться" ведет напрямую в Telegram


@router.callback_query(F.data.startswith("consultation_"))
async def show_consultation_detail(callback: CallbackQuery):
    """Показать детальную информацию о консультации - вся информация в одном сообщении"""
    # Извлекаем slug консультации
    parts = callback.data.split("_")
    
    if len(parts) < 2:
        await callback.answer("Ошибка при загрузке консультации", show_alert=True)
        return
    
    # Убираем префиксы info/details/price если они есть
    if parts[1] in ["info", "details", "price"]:
        consultation_slug = "_".join(parts[2:])
    else:
        consultation_slug = "_".join(parts[1:])
    
    # Получаем консультацию из JSON
    consultation = get_consultation_by_slug(consultation_slug)
    
    if not consultation:
        await callback.answer("Консультация не найдена", show_alert=True)
        return
    
    # Формируем полный текст со всей информацией
    emoji = consultation.get('emoji', '🔮')
    text = f"{emoji} **{consultation['name']}**\n\n"
    
    # Описание
    if consultation.get('short_description'):
        text += f"{consultation['short_description']}\n\n"
    
    # Для кого
    if consultation.get('for_whom'):
        text += f"**Для кого это:**\n{consultation['for_whom']}\n\n"
    
    # Что входит
    if consultation.get('what_included'):
        text += "**Что входит:**\n"
        for item in consultation['what_included']:
            text += f"• {item}\n"
        text += "\n"
    
    # Формат работы
    if consultation.get('format_info'):
        text += f"**Формат работы:**\n{consultation['format_info']}\n\n"
    
    # Результат
    if consultation.get('result'):
        text += f"**Результат:**\n{consultation['result']}\n\n"
    
    # Варианты и стоимость
    options = consultation.get('options', [])
    active_options = [o for o in options if o.get('is_active', True)]
    
    if active_options:
        text += "**Варианты и стоимость:**\n\n"
        
        for option in active_options:
            text += f"**{option['name']}** — {option['price']:,.0f} ₽\n"
            if option.get('description'):
                text += f"{option['description']}\n"
            
            if option.get('duration'):
                text += f"⏱ {option['duration']}\n"
            
            if option.get('features'):
                for feature in option['features']:
                    text += f"  • {feature}\n"
            
            text += "\n"
    else:
        # Если нет вариантов, показываем общую информацию
        if consultation.get('duration'):
            text += f"⏱ **Длительность:** {consultation['duration']}\n"
        
        if consultation.get('price'):
            text += f"💰 **Стоимость:** {consultation['price']:,.0f} ₽\n"
    
    try:
        # Если это видео - удаляем и отправляем новое сообщение
        if callback.message.video:
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_consultation_detail_keyboard(consultation_slug, consultation['name']),
                parse_mode="Markdown"
            )
        else:
            # Если текст - редактируем
            await callback.message.edit_text(
                text,
                reply_markup=get_consultation_detail_keyboard(consultation_slug, consultation['name']),
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
            reply_markup=get_consultation_detail_keyboard(consultation_slug, consultation['name']),
            parse_mode="Markdown"
        )
    
    await callback.answer()

from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database import get_db, User
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
    db = get_db()
    
    try:
        # Обновляем активность
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
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
    
    finally:
        db.close()


# Этот обработчик больше не нужен - запись идет через Telegram
# @router.callback_query(F.data.startswith("consultation_book_"))
# async def show_consultation_booking(callback: CallbackQuery):
#     """Показать варианты консультации для записи"""
#     # Теперь кнопка "Записаться" ведет напрямую в Telegram


@router.callback_query(F.data.startswith("consultation_"))
async def show_consultation_detail(callback: CallbackQuery):
    """Показать детальную информацию о консультации"""
    # Извлекаем slug консультации
    parts = callback.data.split("_")
    
    if len(parts) < 2:
        await callback.answer("Ошибка при загрузке консультации", show_alert=True)
        return
    
    # Проверяем, это навигация или просмотр
    if parts[1] == "info":
        consultation_slug = "_".join(parts[2:])
        show_section = "info"
    elif parts[1] == "details":
        consultation_slug = "_".join(parts[2:])
        show_section = "details"
    elif parts[1] == "price":
        consultation_slug = "_".join(parts[2:])
        show_section = "price"
    else:
        consultation_slug = "_".join(parts[1:])
        show_section = "info"
    
    # Получаем консультацию из JSON
    consultation = get_consultation_by_slug(consultation_slug)
    
    if not consultation:
        await callback.answer("Консультация не найдена", show_alert=True)
        return
    
    # Формируем текст в зависимости от секции
    emoji = consultation.get('emoji', '🔮')
    
    if show_section == "info":
        text = f"{emoji} **{consultation['name']}**\n\n"
        
        if consultation.get('short_description'):
            text += f"{consultation['short_description']}\n\n"
        
        if consultation.get('for_whom'):
            text += f"**Для кого это:**\n{consultation['for_whom']}\n\n"
        
        if consultation.get('duration'):
            text += f"⏱ **Длительность:** {consultation['duration']}\n"
        
        if consultation.get('price'):
            text += f"💰 **Стоимость:** {consultation['price']:,.0f} ₽\n"
    
    elif show_section == "details":
        text = f"{emoji} **{consultation['name']}**\n\n"
        
        if consultation.get('what_included'):
            text += "**Что входит:**\n"
            for item in consultation['what_included']:
                text += f"• {item}\n"
            text += "\n"
        
        if consultation.get('format_info'):
            text += f"**Формат работы:**\n{consultation['format_info']}\n\n"
        
        if consultation.get('result'):
            text += f"**Результат:**\n{consultation['result']}\n"
    
    elif show_section == "price":
        text = f"{emoji} **{consultation['name']}**\n\n"
        
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
            if consultation.get('price'):
                text += f"**Стоимость:** {consultation['price']:,.0f} ₽\n\n"
            if consultation.get('duration'):
                text += f"**Длительность:** {consultation['duration']}\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_consultation_detail_keyboard(consultation_slug),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        # Сообщение не изменилось - это нормально
        pass
    
    await callback.answer()

import json
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.orm import Session

from database import get_db, Consultation, ConsultationOption, User
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
    db: Session = get_db()
    
    try:
        # Обновляем активность
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
        # Получаем активные консультации
        consultations = db.query(Consultation).filter(
            Consultation.is_active == True
        ).order_by(Consultation.order).all()
        
        if not consultations:
            await callback.message.edit_text(
                "🔮 К сожалению, сейчас нет доступных консультаций.",
                reply_markup=get_back_keyboard("main_menu")
            )
        else:
            text = "🔮 **Консультационные услуги**\n\n"
            text += "Выберите интересующую вас услугу для получения подробной информации:"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_consultations_keyboard(consultations),
                parse_mode="Markdown"
            )
        
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("consultation_book_"))
async def show_consultation_booking(callback: CallbackQuery):
    """Показать варианты консультации для записи"""
    consultation_slug = callback.data.replace("consultation_book_", "")
    
    db: Session = get_db()
    
    try:
        # Получаем консультацию
        consultation = db.query(Consultation).filter(
            Consultation.slug == consultation_slug,
            Consultation.is_active == True
        ).first()
        
        if not consultation:
            await callback.answer("Консультация не найдена", show_alert=True)
            return
        
        # Если есть варианты - показываем их
        if consultation.options:
            options = db.query(ConsultationOption).filter(
                ConsultationOption.consultation_id == consultation.id,
                ConsultationOption.is_active == True
            ).order_by(ConsultationOption.order).all()
            
            text = f"📝 **Выберите вариант**\n\n"
            text += f"{consultation.emoji} {consultation.name}\n\n"
            text += "Выберите подходящий вам вариант:"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_consultation_options_keyboard(consultation_slug, options),
                parse_mode="Markdown"
            )
        else:
            # Если нет вариантов - сразу переходим к оплате
            # TODO: Здесь будет создание платежа
            text = f"📝 **Запись на консультацию**\n\n"
            text += f"{consultation.emoji} {consultation.name}\n"
            text += f"💰 Стоимость: {consultation.price:,.0f} ₽\n"
            text += f"⏱ Длительность: {consultation.duration}\n\n"
            text += "Для записи нажмите кнопку «Оплатить»"
            
            # TODO: Добавить кнопку оплаты
            await callback.message.edit_text(
                text,
                reply_markup=get_back_keyboard(f"consultation_{consultation_slug}"),
                parse_mode="Markdown"
            )
        
        await callback.answer()
    
    finally:
        db.close()


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
    
    db: Session = get_db()
    
    try:
        # Получаем консультацию
        consultation = db.query(Consultation).filter(
            Consultation.slug == consultation_slug,
            Consultation.is_active == True
        ).first()
        
        if not consultation:
            await callback.answer("Консультация не найдена", show_alert=True)
            return
        
        # Формируем текст в зависимости от секции
        if show_section == "info":
            text = f"{consultation.emoji} **{consultation.name}**\n\n"
            
            if consultation.short_description:
                text += f"{consultation.short_description}\n\n"
            
            if consultation.for_whom:
                text += f"**Для кого это:**\n{consultation.for_whom}\n\n"
            
            if consultation.duration:
                text += f"⏱ **Длительность:** {consultation.duration}\n"
            
            if consultation.price:
                text += f"💰 **Стоимость:** {consultation.price:,.0f} ₽\n"
        
        elif show_section == "details":
            text = f"{consultation.emoji} **{consultation.name}**\n\n"
            
            if consultation.what_included:
                text += "**Что входит:**\n"
                try:
                    included = json.loads(consultation.what_included)
                    for item in included:
                        text += f"• {item}\n"
                    text += "\n"
                except:
                    text += f"{consultation.what_included}\n\n"
            
            if consultation.format_info:
                text += f"**Формат работы:**\n{consultation.format_info}\n\n"
            
            if consultation.result:
                text += f"**Результат:**\n{consultation.result}\n"
        
        elif show_section == "price":
            text = f"{consultation.emoji} **{consultation.name}**\n\n"
            
            if consultation.options:
                text += "**Варианты и стоимость:**\n\n"
                
                options = db.query(ConsultationOption).filter(
                    ConsultationOption.consultation_id == consultation.id,
                    ConsultationOption.is_active == True
                ).order_by(ConsultationOption.order).all()
                
                for option in options:
                    text += f"**{option.name}** — {option.price:,.0f} ₽\n"
                    if option.description:
                        text += f"{option.description}\n"
                    
                    if option.duration:
                        text += f"⏱ {option.duration}\n"
                    
                    if option.features:
                        try:
                            features = json.loads(option.features)
                            for feature in features:
                                text += f"  • {feature}\n"
                        except:
                            pass
                    
                    text += "\n"
            else:
                if consultation.price:
                    text += f"**Стоимость:** {consultation.price:,.0f} ₽\n\n"
                if consultation.duration:
                    text += f"**Длительность:** {consultation.duration}\n"
        
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
    
    finally:
        db.close()


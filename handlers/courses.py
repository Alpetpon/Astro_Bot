import json
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.orm import Session

from database import get_db, Course, Tariff, User
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
    db: Session = get_db()
    
    try:
        # Обновляем активность
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
        # Получаем активные курсы
        courses = db.query(Course).filter(Course.is_active == True).order_by(Course.order).all()
        
        if not courses:
            await callback.message.edit_text(
                "📚 К сожалению, сейчас нет доступных курсов.",
                reply_markup=get_back_keyboard("main_menu")
            )
        else:
            await callback.message.edit_text(
                "📚 **Каталог курсов**\n\nВыберите интересующий вас курс:",
                reply_markup=get_courses_keyboard(courses),
                parse_mode="Markdown"
            )
        
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("course_register_"))
async def show_tariff_selection(callback: CallbackQuery):
    """Показать выбор тарифа для записи"""
    course_slug = callback.data.replace("course_register_", "")
    
    db: Session = get_db()
    
    try:
        # Получаем курс и его тарифы
        course = db.query(Course).filter(
            Course.slug == course_slug,
            Course.is_active == True
        ).first()
        
        if not course:
            await callback.answer("Курс не найден", show_alert=True)
            return
        
        tariffs = db.query(Tariff).filter(
            Tariff.course_id == course.id,
            Tariff.is_active == True
        ).order_by(Tariff.order).all()
        
        if not tariffs:
            await callback.answer("Тарифы не найдены", show_alert=True)
            return
        
        text = f"📝 **Выберите тариф**\n\n"
        text += f"Курс: {course.name}\n\n"
        text += "Выберите подходящий вам вариант обучения:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_tariff_keyboard(course_slug, tariffs),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        db.close()


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
    
    db: Session = get_db()
    
    try:
        # Получаем курс
        course = db.query(Course).filter(
            Course.slug == course_slug,
            Course.is_active == True
        ).first()
        
        if not course:
            await callback.answer("Курс не найден", show_alert=True)
            return
        
        if show_about:
            # Показываем информацию о курсе
            text = f"📖 **{course.name}**\n\n"
            text += f"{course.description}\n\n"
            
            if course.duration:
                text += f"⏱ **Длительность:** {course.duration}\n\n"
            
            if course.program:
                text += "📋 **Программа:**\n"
                try:
                    program = json.loads(course.program)
                    for module in program:
                        text += f"• {module}\n"
                except:
                    text += course.program
        else:
            # Показываем тарифы
            text = f"💰 **Тарифы курса «{course.name}»**\n\n"
            
            tariffs = db.query(Tariff).filter(
                Tariff.course_id == course.id,
                Tariff.is_active == True
            ).order_by(Tariff.order).all()
            
            for tariff in tariffs:
                support_text = "✅ С сопровождением" if tariff.with_support else "📚 Самостоятельно"
                text += f"**{tariff.name}** - {tariff.price} ₽\n"
                text += f"{support_text}\n"
                text += f"{tariff.description}\n"
                
                if tariff.features:
                    try:
                        features = json.loads(tariff.features)
                        for feature in features:
                            text += f"  • {feature}\n"
                    except:
                        pass
                
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
    
    finally:
        db.close()


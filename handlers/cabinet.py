from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_db, User, Payment
from keyboards import get_back_keyboard
from data import get_course_by_slug, get_consultation_by_slug

router = Router()


@router.callback_query(F.data == "my_cabinet")
async def show_my_cabinet(callback: CallbackQuery):
    """Показать личный кабинет"""
    db = get_db()
    
    try:
        # Обновляем активность
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
        # Получаем информацию о пользователе
        username = callback.from_user.username or "не указан"
        first_name = callback.from_user.first_name or ""
        
        # Проверяем платежи
        payments = db.query(Payment).filter(
            Payment.user_id == user.id,
            Payment.status == 'succeeded'
        ).all()
        
        # Считаем статистику
        courses_count = len([p for p in payments if p.product_type == 'course'])
        consultations_count = len([p for p in payments if p.product_type == 'consultation'])
        guides_count = len([p for p in payments if p.product_type == 'guide'])
        total_spent = sum(p.amount for p in payments)
        
        # Формируем текст
        text = f"🏠 <b>Мой кабинет</b>\n\n"
        text += f"👤 <b>{first_name}</b>\n"
        text += f"🆔 @{username}\n"
        text += f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        
        text += "📊 <b>Моя статистика:</b>\n"
        text += f"📚 Курсов: {courses_count}\n"
        text += f"🔮 Консультаций: {consultations_count}\n"
        text += f"💝 Гайдов: {guides_count}\n"
        text += f"💰 Всего потрачено: {total_spent:,.0f} ₽\n\n"
        
        # Создаём клавиатуру
        buttons = []
        
        if payments:
            text += "💳 <b>Мои покупки:</b>\n\n"
            
            # Группируем покупки по типу
            courses = [p for p in payments if p.product_type == 'course']
            consultations = [p for p in payments if p.product_type == 'consultation']
            
            if courses:
                text += "📚 <b>Курсы:</b>\n"
                for payment in courses:
                    course = get_course_by_slug(payment.course_slug)
                    if course:
                        course_name = course.get('name', payment.course_slug)
                        emoji = course.get('emoji', '📚')
                        text += f"• {emoji} {course_name}\n"
                        # Добавляем кнопку для перехода к курсу
                        buttons.append([InlineKeyboardButton(
                            text=f"{emoji} {course_name}",
                            callback_data=f"course_{payment.course_slug}"
                        )])
                text += "\n"
            
            if consultations:
                text += "🔮 <b>Консультации:</b>\n"
                for payment in consultations:
                    consultation = get_consultation_by_slug(payment.consultation_slug)
                    if consultation:
                        consultation_name = consultation.get('name', payment.consultation_slug)
                        emoji = consultation.get('emoji', '🔮')
                        text += f"• {emoji} {consultation_name}\n"
                        paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                        text += f"  Оплачено: {paid_date}\n"
                text += "\n"
        else:
            text += "📚 У вас пока нет купленных курсов или консультаций.\n\n"
            text += "Перейдите в каталог, чтобы выбрать подходящий курс!"
            
            # Добавляем кнопки для перехода к каталогам
            buttons.append([InlineKeyboardButton(text="📚 Каталог курсов", callback_data="courses")])
            buttons.append([InlineKeyboardButton(text="🔮 Консультации", callback_data="consultations")])
            buttons.append([InlineKeyboardButton(text="💕 Гайды", callback_data="guides_list")])
        
        # Кнопка назад
        buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    
    except Exception as e:
        print(f"Error in show_my_cabinet: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
    
    finally:
        db.close()


# Заглушки для других обработчиков кабинета (на будущее)

@router.callback_query(F.data == "my_courses")
async def show_my_courses(callback: CallbackQuery):
    """Показать мои курсы (заглушка)"""
    await callback.message.edit_text(
        "📚 <b>Мои курсы</b>\n\n"
        "🔧 Раздел находится в разработке.\n"
        "Скоро здесь появятся ваши курсы с доступом к урокам!",
        reply_markup=get_back_keyboard("my_cabinet", "◀️ В кабинет")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("my_course_"))
async def show_my_course(callback: CallbackQuery):
    """Показать конкретный курс (заглушка)"""
    await callback.message.edit_text(
        "📖 <b>Курс</b>\n\n"
        "🔧 Раздел находится в разработке.",
        reply_markup=get_back_keyboard("my_courses", "◀️ К курсам")
    )
    await callback.answer()

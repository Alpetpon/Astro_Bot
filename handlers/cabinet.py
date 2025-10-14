from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.orm import Session

from database import get_db, User, Payment
from data import get_course_by_slug, get_consultation_by_slug
from keyboards import get_back_keyboard

router = Router()


@router.callback_query(F.data == "my_cabinet")
async def show_my_cabinet(callback: CallbackQuery):
    """Показать личный кабинет с оплаченными курсами и консультациями"""
    db: Session = get_db()
    
    try:
        # Обновляем активность
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Получаем все успешные платежи пользователя
        payments = db.query(Payment).filter(
            Payment.user_id == user.id,
            Payment.status == 'succeeded'
        ).order_by(Payment.paid_at.desc()).all()
        
        # Формируем сообщение
        text = "🏠 **Мой кабинет**\n\n"
        
        if not payments:
            text += "У вас пока нет оплаченных курсов или консультаций.\n\n"
            text += "📚 Выберите интересующий курс или консультацию в главном меню!"
        else:
            # Группируем по типам
            courses_slugs = set()
            consultations_slugs = set()
            guides_count = 0
            
            for payment in payments:
                if payment.product_type == 'course' and payment.course_slug:
                    courses_slugs.add(payment.course_slug)
                elif payment.product_type == 'consultation' and payment.consultation_slug:
                    consultations_slugs.add(payment.consultation_slug)
                elif payment.product_type == 'guide':
                    guides_count += 1
            
            # Показываем курсы
            if courses_slugs:
                text += "📚 **Мои курсы:**\n\n"
                for slug in courses_slugs:
                    course = get_course_by_slug(slug)
                    if course:
                        emoji = course.get('emoji', '📚')
                        text += f"{emoji} {course['name']}\n"
                    else:
                        text += f"📚 {slug}\n"
                text += "\n"
            
            # Показываем консультации
            if consultations_slugs:
                text += "🔮 **Мои консультации:**\n\n"
                for slug in consultations_slugs:
                    consultation = get_consultation_by_slug(slug)
                    if consultation:
                        emoji = consultation.get('emoji', '🔮')
                        text += f"{emoji} {consultation['name']}\n"
                    else:
                        text += f"🔮 {slug}\n"
                text += "\n"
            
            # Показываем гайды
            if guides_count > 0:
                text += f"💝 **Гайды:** {guides_count} шт.\n\n"
            
            text += "📩 Если у вас есть вопросы, свяжитесь с поддержкой через @username"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("main_menu", "🏠 В меню"),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    except Exception as e:
        print(f"Error in show_my_cabinet: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
    
    finally:
        db.close()

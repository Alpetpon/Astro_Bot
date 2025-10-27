import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

from database import get_db, UserRepository, PaymentRepository
from keyboards import get_back_keyboard
from data import (
    get_course_by_slug, 
    get_consultation_by_slug,
    get_course_modules,
    get_module_by_id,
    get_lesson_by_id
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_cabinet")
async def show_my_cabinet(callback: CallbackQuery):
    """Показать личный кабинет - статистика покупок"""
    from config import config as bot_config
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        # Обновляем активность
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if user:
            await user_repo.update_activity(callback.from_user.id)
        
        # Проверяем платежи
        payments = await payment_repo.get_user_payments(user.id)
        # Фильтруем только успешные платежи
        payments = [p for p in payments if p.status == 'succeeded']
        
        # Считаем статистику
        courses_count = len([p for p in payments if p.product_type in ['course', 'mini_course']])
        consultations_count = len([p for p in payments if p.product_type == 'consultation'])
        guides_count = len([p for p in payments if p.product_type == 'guide'])
        total_spent = sum(p.amount for p in payments)
        
        # Формируем текст
        text = "<b>💼 Мой кабинет</b>\n\n"
        
        text += "<b>📊 Моя статистика:</b>\n"
        text += f"• Курсов: {courses_count}\n"
        text += f"• Консультаций: {consultations_count}\n"
        text += f"• Гайдов: {guides_count}\n\n"
        text += f"💰 Всего потрачено: {total_spent:,.0f} ₽\n\n"
        
        # Создаём клавиатуру
        buttons = []
        
        if payments:
            text += "<b>🛍 Мои покупки:</b>\n\n"
            
            # Группируем покупки по типу
            courses = [p for p in payments if p.product_type in ['course', 'mini_course']]
            consultations = [p for p in payments if p.product_type == 'consultation']
            
            if courses:
                text += "<b>📚 Курсы:</b>\n"
                for payment in courses:
                    # Проверяем, это мини-курс или обычный курс
                    if payment.course_slug == "mini_course":
                        from data import get_mini_course
                        mini_course = get_mini_course()
                        if mini_course:
                            course_name = mini_course.get('title', 'Мини-курс')
                            emoji = mini_course.get('emoji', '🌌')
                            paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                            text += f"• {emoji} {course_name}\n"
                            text += f"  Куплено: {paid_date}\n"
                    else:
                        course = get_course_by_slug(payment.course_slug)
                        if course:
                            course_name = course.get('name', payment.course_slug)
                            emoji = course.get('emoji', '📚')
                            paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                            text += f"• {emoji} {course_name}\n"
                            text += f"  Куплено: {paid_date}\n"
                
                text += "\n🎓 <b>Для изучения материалов нажмите кнопку ниже:</b>\n\n"
                
                # Добавляем кнопку для перехода в учебный бот
                buttons.append([InlineKeyboardButton(
                    text="🎓 Перейти к обучению",
                    url=f"https://t.me/{bot_config.LEARNING_BOT_USERNAME}"
                )])
            
            if consultations:
                text += "<b>🔮 Консультации:</b>\n"
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
        
        try:
            # Если это видео - удаляем и отправляем новое сообщение
            if callback.message.video:
                await callback.message.delete()
                await callback.bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=text,
                    reply_markup=keyboard
                )
            else:
                # Если текст - редактируем
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard
                )
        except Exception as edit_error:
            # Если не можем отредактировать - удаляем и отправляем новое
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=keyboard
            )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_my_cabinet: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "my_courses")
async def show_my_courses(callback: CallbackQuery):
    """Перенаправление на личный кабинет (для совместимости)"""
    # Перенаправляем на my_cabinet
    await show_my_cabinet(callback)


# Удалены хэндлеры для материалов курсов - они теперь в учебном боте (learning_bot.py)
# my_course_, module_, lesson_, download_lecture_, mini_module_, mini_lesson_

from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.orm import Session

from database import (
    get_db, User, Course, Tariff, Payment, 
    UserProgress, Lesson
)
from keyboards import get_payment_keyboard, get_back_keyboard
from payments import YooKassaPayment

router = Router()
yookassa = YooKassaPayment()


@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery):
    """Обработка выбора тарифа и создание платежа"""
    tariff_id = int(callback.data.replace("tariff_", ""))
    
    db: Session = get_db()
    
    try:
        # Получаем тариф и курс
        tariff = db.query(Tariff).filter(Tariff.id == tariff_id).first()
        
        if not tariff:
            await callback.answer("Тариф не найден", show_alert=True)
            return
        
        course = db.query(Course).filter(Course.id == tariff.course_id).first()
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        if not course or not user:
            await callback.answer("Ошибка при создании платежа", show_alert=True)
            return
        
        # Создаем платеж в базе
        payment = Payment(
            user_id=user.id,
            course_id=course.id,
            tariff_id=tariff.id,
            amount=tariff.price,
            status='pending'
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Создаем платеж в ЮKassa
        description = f"Оплата курса «{course.name}» - {tariff.name}"
        
        # Получаем информацию о боте для return_url
        bot_info = await callback.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_result = yookassa.create_payment(
            amount=tariff.price,
            description=description,
            return_url=return_url
        )
        
        if not payment_result:
            payment.status = 'failed'
            db.commit()
            await callback.message.edit_text(
                "❌ Ошибка при создании платежа. Попробуйте позже.",
                reply_markup=get_back_keyboard("courses")
            )
            await callback.answer()
            return
        
        # Обновляем платеж данными из ЮKassa
        payment.payment_id = payment_result['id']
        payment.confirmation_url = payment_result['confirmation_url']
        db.commit()
        
        # Формируем сообщение об оплате
        support_text = "✅ С сопровождением куратора" if tariff.with_support else "📚 Самостоятельное обучение"
        
        text = f"💳 **Оплата курса**\n\n"
        text += f"**Курс:** {course.name}\n"
        text += f"**Тариф:** {tariff.name}\n"
        text += f"**Формат:** {support_text}\n"
        text += f"**Стоимость:** {tariff.price} ₽\n\n"
        text += "Нажмите кнопку «Оплатить» для перехода на страницу оплаты.\n"
        text += "После успешной оплаты доступ к курсу откроется автоматически!"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(payment_result['confirmation_url'], payment.id),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    except Exception as e:
        print(f"Error in process_tariff_selection: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Проверка статуса платежа"""
    payment_id = int(callback.data.replace("check_payment_", ""))
    
    db: Session = get_db()
    
    try:
        # Получаем платеж из базы
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        
        if not payment:
            await callback.answer("Платеж не найден", show_alert=True)
            return
        
        # Если платеж уже успешен
        if payment.status == 'succeeded':
            await callback.answer("✅ Платеж уже обработан!", show_alert=True)
            return
        
        # Проверяем статус в ЮKassa
        if payment.payment_id:
            payment_status = yookassa.get_payment_status(payment.payment_id)
            
            if payment_status and payment_status['status'] == 'succeeded':
                # Обновляем платеж
                payment.status = 'succeeded'
                payment.paid_at = datetime.utcnow()
                db.commit()
                
                # Выдаем доступ к курсу
                await grant_course_access(db, payment)
                
                # Уведомляем пользователя
                course = db.query(Course).filter(Course.id == payment.course_id).first()
                tariff = db.query(Tariff).filter(Tariff.id == payment.tariff_id).first()
                
                success_text = "✅ **Оплата успешна!**\n\n"
                success_text += f"Вам открыт доступ к курсу «{course.name}»\n\n"
                
                if tariff.with_support:
                    success_text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
                
                success_text += "📚 Перейдите в «Мой кабинет» для начала обучения!"
                
                await callback.message.edit_text(
                    success_text,
                    reply_markup=get_back_keyboard("my_cabinet", "🏠 Мой кабинет"),
                    parse_mode="Markdown"
                )
                await callback.answer("✅ Доступ открыт!", show_alert=True)
            else:
                await callback.answer("⏳ Платеж еще не обработан. Попробуйте через минуту.", show_alert=True)
        else:
            await callback.answer("❌ Ошибка проверки платежа", show_alert=True)
    
    except Exception as e:
        print(f"Error in check_payment_status: {e}")
        await callback.answer("Произошла ошибка при проверке платежа", show_alert=True)
    
    finally:
        db.close()


async def grant_course_access(db: Session, payment: Payment):
    """Выдача доступа к курсу после оплаты"""
    try:
        # Получаем все уроки курса
        lessons = db.query(Lesson).filter(
            Lesson.course_id == payment.course_id
        ).order_by(Lesson.module_number, Lesson.lesson_number).all()
        
        # Создаем записи прогресса для всех уроков
        for idx, lesson in enumerate(lessons):
            # Первый урок первого модуля доступен сразу
            is_available = (idx == 0)
            
            progress = UserProgress(
                user_id=payment.user_id,
                lesson_id=lesson.id,
                course_id=payment.course_id,
                is_available=is_available,
                is_completed=False
            )
            db.add(progress)
        
        db.commit()
        print(f"Access granted for user {payment.user_id} to course {payment.course_id}")
    
    except Exception as e:
        print(f"Error in grant_course_access: {e}")
        db.rollback()


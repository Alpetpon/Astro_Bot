from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.orm import Session

from database import (
    get_db, User, Course, Tariff, Payment, 
    UserProgress, Lesson, Consultation, ConsultationOption
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


@router.callback_query(F.data.startswith("consultation_option_"))
async def process_consultation_option_selection(callback: CallbackQuery):
    """Обработка выбора варианта консультации и создание платежа"""
    option_id = int(callback.data.replace("consultation_option_", ""))
    
    db: Session = get_db()
    
    try:
        # Получаем вариант консультации
        option = db.query(ConsultationOption).filter(ConsultationOption.id == option_id).first()
        
        if not option:
            await callback.answer("Вариант не найден", show_alert=True)
            return
        
        consultation = db.query(Consultation).filter(Consultation.id == option.consultation_id).first()
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        if not consultation or not user:
            await callback.answer("Ошибка при создании платежа", show_alert=True)
            return
        
        # Создаем платеж в базе
        payment = Payment(
            user_id=user.id,
            consultation_id=consultation.id,
            consultation_option_id=option.id,
            amount=option.price,
            status='pending',
            product_type='consultation'
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Создаем платеж в ЮKassa
        description = f"Оплата консультации «{consultation.name}» - {option.name}"
        
        # Получаем информацию о боте для return_url
        bot_info = await callback.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_result = yookassa.create_payment(
            amount=option.price,
            description=description,
            return_url=return_url
        )
        
        if not payment_result:
            payment.status = 'failed'
            db.commit()
            await callback.message.edit_text(
                "❌ Ошибка при создании платежа. Попробуйте позже.",
                reply_markup=get_back_keyboard("consultations")
            )
            await callback.answer()
            return
        
        # Обновляем платеж данными из ЮKassa
        payment.payment_id = payment_result['id']
        payment.confirmation_url = payment_result['confirmation_url']
        db.commit()
        
        # Формируем сообщение об оплате
        text = f"💳 **Оплата консультации**\n\n"
        text += f"**Услуга:** {consultation.name}\n"
        text += f"**Вариант:** {option.name}\n"
        if option.duration:
            text += f"**Длительность:** {option.duration}\n"
        text += f"**Стоимость:** {option.price:,.0f} ₽\n\n"
        text += "Нажмите кнопку «Оплатить» для перехода на страницу оплаты.\n"
        text += "После успешной оплаты с вами свяжется астролог для согласования времени встречи!"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(payment_result['confirmation_url'], payment.id),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    except Exception as e:
        print(f"Error in process_consultation_option_selection: {e}")
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
                
                # Проверяем тип продукта
                if payment.product_type == 'guide':
                    # Отправляем гайд
                    await send_guide_to_user(callback, payment)
                elif payment.product_type == 'consultation':
                    # Уведомляем об оплате консультации
                    consultation = db.query(Consultation).filter(Consultation.id == payment.consultation_id).first()
                    
                    success_text = "✅ **Оплата успешна!**\n\n"
                    success_text += f"{consultation.emoji} Консультация «{consultation.name}» оплачена!\n\n"
                    success_text += "📞 В ближайшее время с вами свяжется астролог для согласования времени встречи.\n\n"
                    success_text += "Спасибо за доверие! 🌟"
                    
                    await callback.message.edit_text(
                        success_text,
                        reply_markup=get_back_keyboard("main_menu", "🏠 Главное меню"),
                        parse_mode="Markdown"
                    )
                    await callback.answer("✅ Оплата подтверждена!", show_alert=True)
                else:
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


async def send_guide_to_user(callback: CallbackQuery, payment: Payment):
    """Отправка гайда пользователю после оплаты"""
    from config import config
    from aiogram.types import FSInputFile
    import os
    
    try:
        # Находим гайд по product_id
        guide_id = payment.product_id
        guide = next((g for g in config.GUIDES if g['id'] == guide_id), None)
        
        if not guide:
            await callback.message.answer(
                "✅ **Оплата успешна!**\n\n"
                "Гайд будет отправлен вам в течение нескольких минут.\n"
                "Если возникнут вопросы, свяжитесь с поддержкой.",
                parse_mode="Markdown"
            )
            return
        
        guide_file = guide.get('file_id', '')
        
        if not guide_file:
            await callback.message.answer(
                "✅ **Оплата успешна!**\n\n"
                "Гайд будет отправлен вам в течение нескольких минут.\n"
                "Если возникнут вопросы, свяжитесь с поддержкой.",
                parse_mode="Markdown"
            )
            return
        
        # Отправляем файл гайда
        if os.path.exists(guide_file):
            # Если это локальный файл, отправляем документ
            document = FSInputFile(guide_file)
            await callback.message.answer_document(
                document=document,
                caption=f"✅ **Оплата успешна!**\n\n{guide['emoji']} Ваш {guide['name']} готов!\n\nЖелаем вам гармоничных отношений! 🌟",
                parse_mode="Markdown"
            )
            await callback.message.answer(
                "Приятного изучения! 📖",
                reply_markup=get_back_keyboard("main_menu", "🏠 Главное меню")
            )
        else:
            # Если file_id Telegram
            await callback.message.answer_document(
                document=guide_file,
                caption=f"✅ **Оплата успешна!**\n\n{guide['emoji']} Ваш {guide['name']} готов!\n\nЖелаем вам гармоничных отношений! 🌟",
                parse_mode="Markdown"
            )
            await callback.message.answer(
                "Приятного изучения! 📖",
                reply_markup=get_back_keyboard("main_menu", "🏠 Главное меню")
            )
        
        await callback.answer("✅ Гайд отправлен!", show_alert=True)
        
    except Exception as e:
        print(f"Error sending guide: {e}")
        await callback.message.answer(
            "✅ **Оплата успешна!**\n\n"
            "Произошла ошибка при отправке файла. Пожалуйста, свяжитесь с поддержкой.",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard("main_menu", "🏠 Главное меню")
        )


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


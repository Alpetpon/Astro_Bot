import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_db, User, Payment
from data import get_course_by_slug, get_tariff_by_id, get_consultation_by_slug, get_consultation_option, get_guide_by_id
from keyboards import get_payment_keyboard, get_back_keyboard
from payments import YooKassaPayment

logger = logging.getLogger(__name__)
router = Router()
yookassa = YooKassaPayment()


@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery):
    """Обработка выбора тарифа и создание платежа"""
    logger.info(f"User {callback.from_user.id} selecting tariff: {callback.data}")
    
    # Формат: tariff_{course_slug}_{tariff_id}
    parts = callback.data.split("_", 2)
    if len(parts) < 3:
        logger.warning(f"Invalid tariff callback data format: {callback.data}")
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    
    course_slug = parts[1]
    tariff_id = parts[2]
    
    db = get_db()
    
    try:
        # Получаем курс и тариф из JSON
        course = get_course_by_slug(course_slug)
        if not course:
            logger.warning(f"Course not found: {course_slug}")
            await callback.answer("Курс не найден", show_alert=True)
            return
        
        tariff = get_tariff_by_id(course_slug, tariff_id)
        if not tariff:
            logger.warning(f"Tariff not found: {tariff_id} for course {course_slug}")
            await callback.answer("Тариф не найден", show_alert=True)
            return
        
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            logger.error(f"User not found in database: {callback.from_user.id}")
            await callback.answer("Ошибка при создании платежа", show_alert=True)
            return
        
        # Создаем платеж в базе (теперь с slug вместо FK)
        payment = Payment(
            user_id=user.id,
            course_slug=course_slug,
            tariff_id=tariff_id,
            amount=tariff['price'],
            status='pending',
            product_type='course'
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        logger.info(f"Payment created in DB: {payment.id} for user {user.id}")
        
        # Создаем платеж в ЮKassa
        description = f"Оплата курса «{course['name']}» - {tariff['name']}"
        
        # Получаем информацию о боте для return_url
        bot_info = await callback.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_result = yookassa.create_payment(
            amount=tariff['price'],
            description=description,
            return_url=return_url
        )
        
        if not payment_result:
            payment.status = 'failed'
            db.commit()
            logger.error(f"Failed to create payment in YooKassa for payment {payment.id}")
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
        support_text = "✅ С сопровождением куратора" if tariff.get('with_support') else "📚 Самостоятельное обучение"
        
        text = f"💳 **Оплата курса**\n\n"
        text += f"**Курс:** {course['name']}\n"
        text += f"**Тариф:** {tariff['name']}\n"
        text += f"**Формат:** {support_text}\n"
        text += f"**Стоимость:** {tariff['price']} ₽\n\n"
        text += "Нажмите кнопку «Оплатить» для перехода на страницу оплаты.\n"
        text += "После успешной оплаты доступ к курсу откроется автоматически!"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(payment_result['confirmation_url'], payment.id),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in process_tariff_selection: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("consultation_option_"))
async def process_consultation_option_selection(callback: CallbackQuery):
    """Обработка выбора варианта консультации и создание платежа"""
    logger.info(f"User {callback.from_user.id} selecting consultation option: {callback.data}")
    
    # Формат: consultation_option_{consultation_slug}_{option_id}
    parts = callback.data.split("_", 3)
    if len(parts) < 4:
        logger.warning(f"Invalid consultation callback data format: {callback.data}")
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    
    consultation_slug = parts[2]
    option_id = parts[3]
    
    db = get_db()
    
    try:
        # Получаем консультацию и опцию из JSON
        consultation = get_consultation_by_slug(consultation_slug)
        if not consultation:
            await callback.answer("Консультация не найдена", show_alert=True)
            return
        
        option = get_consultation_option(consultation, option_id)
        if not option:
            await callback.answer("Вариант не найден", show_alert=True)
            return
        
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("Ошибка при создании платежа", show_alert=True)
            return
        
        # Создаем платеж в базе (теперь с slug вместо FK)
        payment = Payment(
            user_id=user.id,
            consultation_slug=consultation_slug,
            consultation_option_id=option_id,
            amount=option['price'],
            status='pending',
            product_type='consultation'
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Создаем платеж в ЮKassa
        description = f"Оплата консультации «{consultation['name']}» - {option['name']}"
        
        # Получаем информацию о боте для return_url
        bot_info = await callback.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_result = yookassa.create_payment(
            amount=option['price'],
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
        text += f"**Услуга:** {consultation['name']}\n"
        text += f"**Вариант:** {option['name']}\n"
        if option.get('duration'):
            text += f"**Длительность:** {option['duration']}\n"
        text += f"**Стоимость:** {option['price']:,.0f} ₽\n\n"
        text += "Нажмите кнопку «Оплатить» для перехода на страницу оплаты.\n"
        text += "После успешной оплаты с вами свяжется астролог для согласования времени встречи!"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(payment_result['confirmation_url'], payment.id),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in process_consultation_option_selection: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Проверка статуса платежа"""
    payment_id = int(callback.data.replace("check_payment_", ""))
    
    logger.info(f"User {callback.from_user.id} checking payment status: {payment_id}")
    
    db = get_db()
    
    try:
        # Получаем платеж из базы
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        
        if not payment:
            logger.warning(f"Payment {payment_id} not found in database")
            await callback.answer("Платеж не найден", show_alert=True)
            return
        
        # Если платеж уже успешен
        if payment.status == 'succeeded':
            logger.info(f"Payment {payment_id} already succeeded")
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
                
                logger.info(f"Payment {payment_id} status updated to succeeded")
                
                # Проверяем тип продукта
                if payment.product_type == 'guide':
                    # Отправляем гайд
                    await send_guide_to_user(callback, payment)
                elif payment.product_type == 'consultation':
                    # Уведомляем об оплате консультации
                    consultation = get_consultation_by_slug(payment.consultation_slug)
                    
                    if consultation:
                        success_text = "✅ **Оплата успешна!**\n\n"
                        success_text += f"{consultation.get('emoji', '🔮')} Консультация «{consultation['name']}» оплачена!\n\n"
                        success_text += "📞 В ближайшее время с вами свяжется астролог для согласования времени встречи.\n\n"
                        success_text += "Спасибо за доверие! 🌟"
                        
                        await callback.message.edit_text(
                            success_text,
                            reply_markup=get_back_keyboard("main_menu", "🏠 Главное меню"),
                            parse_mode="Markdown"
                        )
                        await callback.answer("✅ Оплата подтверждена!", show_alert=True)
                    else:
                        await callback.answer("✅ Оплата подтверждена!", show_alert=True)
                else:
                    # Курс оплачен
                    course = get_course_by_slug(payment.course_slug)
                    tariff = get_tariff_by_id(payment.course_slug, payment.tariff_id) if course else None
                    
                    if course:
                        success_text = "✅ **Оплата успешна!**\n\n"
                        success_text += f"Вам открыт доступ к курсу «{course['name']}»\n\n"
                        
                        if tariff and tariff.get('with_support'):
                            success_text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
                        
                        success_text += "📚 Материалы курса скоро будут доступны в вашем кабинете!"
                        
                        await callback.message.edit_text(
                            success_text,
                            reply_markup=get_back_keyboard("main_menu", "🏠 Главное меню"),
                            parse_mode="Markdown"
                        )
                        await callback.answer("✅ Доступ открыт!", show_alert=True)
                    else:
                        await callback.answer("✅ Оплата подтверждена!", show_alert=True)
            else:
                await callback.answer("⏳ Платеж еще не обработан. Попробуйте через минуту.", show_alert=True)
        else:
            await callback.answer("❌ Ошибка проверки платежа", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in check_payment_status: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при проверке платежа", show_alert=True)
    
    finally:
        db.close()


async def send_guide_to_user(callback: CallbackQuery, payment: Payment):
    """Отправка гайда пользователю после оплаты"""
    try:
        # Находим гайд по product_id (guide_id) из JSON
        guide_id = payment.product_id
        guide = get_guide_by_id(guide_id)
        
        if not guide:
            await callback.message.answer(
                "✅ **Оплата успешна!**\n\n"
                "Гайд будет отправлен вам в течение нескольких минут.\n"
                "Если возникнут вопросы, свяжитесь с поддержкой.",
                parse_mode="Markdown"
            )
            return
        
        file_id = guide.get('file_id')
        
        if not file_id:
            await callback.message.answer(
                "✅ **Оплата успешна!**\n\n"
                "Гайд будет отправлен вам в течение нескольких минут.\n"
                "Если возникнут вопросы, свяжитесь с поддержкой.",
                parse_mode="Markdown"
            )
            return
        
        # Отправляем файл гайда
        await callback.message.answer_document(
            document=file_id,
            caption=f"✅ **Оплата успешна!**\n\n{guide.get('emoji') or '💝'} Ваш {guide['name']} готов!\n\nЖелаем вам успехов в изучении! 🌟",
            parse_mode="Markdown"
        )
        
        # Создаем клавиатуру с кнопками
        buttons = []
        
        # Если есть связанный курс, добавляем кнопку перехода
        if guide.get('related_course_slug'):
            buttons.append([InlineKeyboardButton(
                text="📚 Перейти к курсу",
                callback_data=f"course_{guide['related_course_slug']}"
            )])
        
        # Кнопки навигации
        buttons.append([
            InlineKeyboardButton(text="◀️ К гайдам", callback_data="guides_list"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Отправляем сообщение с кнопками
        await callback.message.answer(
            "Приятного изучения! 📖\n\nВыберите действие:",
            reply_markup=keyboard
        )
        
        await callback.answer("✅ Гайд отправлен!", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error sending guide: {e}", exc_info=True)
        await callback.message.answer(
            "✅ **Оплата успешна!**\n\n"
            "Произошла ошибка при отправке файла. Пожалуйста, свяжитесь с поддержкой.",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard("main_menu", "🏠 Главное меню")
        )

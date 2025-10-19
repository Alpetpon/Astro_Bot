import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

from database import get_db, User, Payment, UserRepository, PaymentRepository
from data import get_course_by_slug, get_tariff_by_id, get_consultation_by_slug, get_consultation_option, get_guide_by_id, get_mini_course, get_mini_course_tariff
from keyboards import get_payment_keyboard, get_back_keyboard
from payments import YooKassaPayment

logger = logging.getLogger(__name__)
router = Router()
yookassa = YooKassaPayment()


@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery):
    """Обработка выбора тарифа и создание платежа"""
    logger.info(f"User {callback.from_user.id} selecting tariff: {callback.data}")
    
    # Проверяем, это мини-курс или обычный курс
    if callback.data.startswith("tariff_mini_course_"):
        # Формат: tariff_mini_course_{tariff_id}
        course_slug = "mini_course"
        tariff_id = callback.data.replace("tariff_mini_course_", "")
    else:
        # Формат: tariff_{course_slug}_{tariff_id}
        parts = callback.data.split("_", 2)
        if len(parts) < 3:
            logger.warning(f"Invalid tariff callback data format: {callback.data}")
            await callback.answer("Ошибка формата данных", show_alert=True)
            return
        
        course_slug = parts[1]
        tariff_id = parts[2]
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        # Определяем, это мини-курс или обычный курс
        if course_slug == "mini_course":
            # Получаем мини-курс и тариф
            mini_course = get_mini_course()
            if not mini_course or not mini_course.get('is_active', False):
                logger.warning("Mini course not found or inactive")
                await callback.answer("Мини-курс недоступен", show_alert=True)
                return
            
            tariff = get_mini_course_tariff(tariff_id)
            if not tariff:
                logger.warning(f"Mini course tariff not found: {tariff_id}")
                await callback.answer("Тариф не найден", show_alert=True)
                return
            
            product_name = f"{mini_course.get('title', 'Мини-курс')} {mini_course.get('subtitle', '')}"
            product_type = 'mini_course'
        else:
            # Получаем обычный курс и тариф из JSON
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
            
            product_name = course['name']
            product_type = 'course'
        
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            logger.error(f"User not found in database: {callback.from_user.id}")
            await callback.answer("Ошибка при создании платежа", show_alert=True)
            return
        
        # Создаем платеж в базе
        payment = Payment(
            user_id=user.id,
            course_slug=course_slug,
            tariff_id=tariff_id,
            amount=tariff['price'],
            status='pending',
            product_type=product_type
        )
        payment = await payment_repo.create(payment)
        
        logger.info(f"Payment created in DB: {payment.id} for user {user.id}")
        
        # Создаем платеж в ЮKassa
        description = f"Оплата: «{product_name}» - {tariff['name']}"
        
        # Получаем информацию о боте для return_url
        bot_info = await callback.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_result = yookassa.create_payment(
            amount=tariff['price'],
            description=description,
            return_url=return_url
        )
        
        if not payment_result:
            await payment_repo.update(payment.id, {"status": "failed"})
            logger.error(f"Failed to create payment in YooKassa for payment {payment.id}")
            back_callback = "mini_course" if product_type == 'mini_course' else "courses"
            await callback.message.edit_text(
                "❌ Ошибка при создании платежа. Попробуйте позже.",
                reply_markup=get_back_keyboard(back_callback)
            )
            await callback.answer()
            return
        
        # Обновляем платеж данными из ЮKassa
        await payment_repo.update(payment.id, {
            "payment_id": payment_result['id'],
            "confirmation_url": payment_result['confirmation_url']
        })
        
        # Формируем сообщение об оплате
        support_text = "✅ С сопровождением куратора" if tariff.get('with_support') else "📚 Самостоятельное обучение"
        
        product_label = "Мини-курс" if product_type == 'mini_course' else "Курс"
        text = f"💳 **Оплата {product_label.lower()}а**\n\n"
        text += f"**{product_label}:** {product_name}\n"
        text += f"**Тариф:** {tariff['name']}\n"
        text += f"**Формат:** {support_text}\n"
        text += f"**Стоимость:** {tariff['price']} ₽\n\n"
        text += "Нажмите кнопку «Оплатить» для перехода на страницу оплаты.\n"
        text += f"После успешной оплаты доступ к {product_label.lower()}у откроется автоматически!"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(payment_result['confirmation_url'], str(payment.id)),
            parse_mode="Markdown"
        )
        
        # Сохраняем chat_id и message_id для последующего редактирования
        await payment_repo.update(payment.id, {
            "chat_id": callback.message.chat.id,
            "message_id": callback.message.message_id
        })
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in process_tariff_selection: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Проверка статуса платежа"""
    payment_id_str = callback.data.replace("check_payment_", "")
    
    try:
        payment_id = ObjectId(payment_id_str)
    except Exception:
        await callback.answer("Неверный ID платежа", show_alert=True)
        return
    
    logger.info(f"User {callback.from_user.id} checking payment status: {payment_id}")
    
    db = await get_db()
    payment_repo = PaymentRepository(db)
    
    try:
        # Получаем платеж из базы
        payment = await payment_repo.get_by_id(payment_id)
        
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
                await payment_repo.update(payment.id, {
                    "status": "succeeded",
                    "paid_at": datetime.utcnow()
                })
                
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
                    # Курс или мини-курс оплачен
                    if payment.course_slug == "mini_course":
                        # Мини-курс
                        mini_course = get_mini_course()
                        tariff = get_mini_course_tariff(payment.tariff_id) if mini_course else None
                        
                        if mini_course:
                            success_text = f"🎉 Поздравляем с покупкой!\n\n"
                            success_text += f"Вам открыт доступ к мини-курсу «{mini_course.get('title', 'Мини-курс')}»\n\n"
                            
                            if tariff and tariff.get('with_support'):
                                success_text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
                            
                            success_text += "📚 Материалы курса доступны в вашем кабинете!"
                            
                            # Создаем кнопку "Мои курсы"
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")]
                            ])
                            
                            await callback.message.edit_text(
                                success_text,
                                reply_markup=keyboard,
                                parse_mode="HTML"
                            )
                            await callback.answer("✅ Доступ открыт!", show_alert=True)
                        else:
                            await callback.answer("✅ Оплата подтверждена!", show_alert=True)
                    else:
                        # Обычный курс
                        course = get_course_by_slug(payment.course_slug)
                        tariff = get_tariff_by_id(payment.course_slug, payment.tariff_id) if course else None
                        
                        if course:
                            success_text = f"🎉 Поздравляем с покупкой!\n\n"
                            success_text += f"Вам открыт доступ к курсу «{course['name']}»\n\n"
                            
                            if tariff and tariff.get('with_support'):
                                success_text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
                            
                            success_text += "📚 Материалы курса доступны в вашем кабинете!"
                            
                            # Создаем кнопку "Мои курсы"
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")]
                            ])
                            
                            await callback.message.edit_text(
                                success_text,
                                reply_markup=keyboard,
                                parse_mode="HTML"
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

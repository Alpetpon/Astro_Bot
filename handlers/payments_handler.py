import logging
from datetime import datetime
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from bson import ObjectId

from database import get_db, User, Payment, UserRepository, PaymentRepository
from data import get_course_by_slug, get_tariff_by_id, get_consultation_by_slug, get_consultation_option, get_guide_by_id, get_mini_course, get_mini_course_tariff
from keyboards import get_payment_keyboard, get_back_keyboard
from payments import YooKassaPayment

logger = logging.getLogger(__name__)
router = Router()
yookassa = YooKassaPayment()


class PaymentEmailStates(StatesGroup):
    """Состояния для запроса email при оплате"""
    waiting_for_email = State()


@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора тарифа и запрос email"""
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
        
        # Сохраняем данные в state для последующего создания платежа
        await state.update_data(
            course_slug=course_slug,
            tariff_id=tariff_id,
            product_name=product_name,
            product_type=product_type,
            tariff_name=tariff['name'],
            tariff_price=tariff['price'],
            tariff_with_support=tariff.get('with_support', False)
        )
        
        # Запрашиваем email
        await state.set_state(PaymentEmailStates.waiting_for_email)
        
        # Отправляем сообщение с запросом email
        await callback.message.edit_text(
            "📧 **Введите ваш email**\n\n"
            "На указанную почту будет отправлен чек об оплате.\n\n"
            "Пример: example@mail.ru",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payment")]
            ])
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in process_tariff_selection: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_request(callback: CallbackQuery, state: FSMContext):
    """Отмена запроса на оплату"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Оплата отменена.",
        reply_markup=get_back_keyboard("main_menu")
    )
    await callback.answer()


@router.message(StateFilter(PaymentEmailStates.waiting_for_email))
async def process_email_and_create_payment(message: Message, state: FSMContext):
    """Обработка введенного email и создание платежа"""
    email = message.text.strip()
    
    # Валидация email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        await message.answer(
            "❌ Неверный формат email. Пожалуйста, введите корректный email.\n\n"
            "Пример: example@mail.ru",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_payment")]
            ])
        )
        return
    
    # Получаем сохраненные данные
    data = await state.get_data()
    course_slug = data.get('course_slug')
    tariff_id = data.get('tariff_id')
    product_name = data.get('product_name')
    product_type = data.get('product_type')
    tariff_name = data.get('tariff_name')
    tariff_price = data.get('tariff_price')
    tariff_with_support = data.get('tariff_with_support', False)
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            logger.error(f"User not found in database: {message.from_user.id}")
            await message.answer("❌ Ошибка при создании платежа. Попробуйте позже.")
            await state.clear()
            return
        
        # Создаем платеж в базе
        payment = Payment(
            user_id=user.id,
            course_slug=course_slug,
            tariff_id=tariff_id,
            amount=tariff_price,
            status='pending',
            product_type=product_type
        )
        payment = await payment_repo.create(payment)
        
        logger.info(f"Payment created in DB: {payment.id} for user {user.id}")
        
        # Создаем платеж в ЮKassa с email
        description = f"Оплата: «{product_name}» - {tariff_name}"
        
        # Получаем информацию о боте для return_url
        bot_info = await message.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_result = yookassa.create_payment(
            amount=tariff_price,
            description=description,
            return_url=return_url,
            customer_email=email
        )
        
        if not payment_result:
            await payment_repo.update(payment.id, {"status": "failed"})
            logger.error(f"Failed to create payment in YooKassa for payment {payment.id}")
            back_callback = "mini_course" if product_type == 'mini_course' else "courses"
            await message.answer(
                "❌ Ошибка при создании платежа. Попробуйте позже.",
                reply_markup=get_back_keyboard(back_callback)
            )
            await state.clear()
            return
        
        # Обновляем платеж данными из ЮKassa
        await payment_repo.update(payment.id, {
            "payment_id": payment_result['id'],
            "confirmation_url": payment_result['confirmation_url']
        })
        
        # Формируем сообщение об оплате
        support_text = "✅ С сопровождением куратора" if tariff_with_support else "📚 Самостоятельное обучение"
        
        product_label = "Мини-курс" if product_type == 'mini_course' else "Курс"
        text = f"💳 **Оплата {product_label.lower()}а**\n\n"
        text += f"**{product_label}:** {product_name}\n"
        text += f"**Тариф:** {tariff_name}\n"
        text += f"**Формат:** {support_text}\n"
        text += f"**Стоимость:** {tariff_price} ₽\n"
        text += f"**Email для чека:** {email}\n\n"
        text += "• Нажмите кнопку «Оплатить» для перехода на страницу оплаты.\n"
        
        # Добавляем информацию для тарифов без обратной связи
        if not tariff_with_support:
            text += "• При покупке курса без обратной связи изучение можно начать сразу после покупки.\n"
        
        text += f"• После успешной оплаты доступ к {product_label.lower()}у откроется автоматически!"
        
        # Определяем callback для кнопки "Назад"
        back_callback = "mini_course_price" if product_type == 'mini_course' else f"course_{course_slug}"
        
        sent_message = await message.answer(
            text,
            reply_markup=get_payment_keyboard(payment_result['confirmation_url'], str(payment.id), back_callback),
            parse_mode="Markdown"
        )
        
        # Сохраняем chat_id и message_id для последующего редактирования
        await payment_repo.update(payment.id, {
            "chat_id": sent_message.chat.id,
            "message_id": sent_message.message_id
        })
        
        # Очищаем state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_email_and_create_payment: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await state.clear()


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
                    # Курс или мини-курс оплачен - отправляем ссылку на учебный бот
                    from config import config as bot_config
                    
                    if payment.course_slug == "mini_course":
                        # Мини-курс
                        mini_course = get_mini_course()
                        tariff = get_mini_course_tariff(payment.tariff_id) if mini_course else None
                        
                        if mini_course:
                            success_text = f"🎉 Поздравляем с покупкой!\n\n"
                            success_text += f"Вам открыт доступ к мини-курсу «{mini_course.get('title', 'Мини-курс')}»\n\n"
                            
                            if tariff and tariff.get('with_support'):
                                success_text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
                            
                            success_text += "🎓 Для изучения материалов нажмите кнопку ниже:"
                            
                            # Создаем кнопку для перехода в учебный бот
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(
                                    text="🎓 Перейти к обучению",
                                    url=f"https://t.me/{bot_config.LEARNING_BOT_USERNAME}"
                                )],
                                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
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
                            
                            success_text += "🎓 Для изучения материалов нажмите кнопку ниже:"
                            
                            # Создаем кнопку для перехода в учебный бот
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(
                                    text="🎓 Перейти к обучению",
                                    url=f"https://t.me/{bot_config.LEARNING_BOT_USERNAME}"
                                )],
                                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
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
        
        # Создаем клавиатуру с кнопками
        buttons = []
        
        # Если есть связанный курс, добавляем кнопку перехода
        if guide.get('related_course_slug'):
            buttons.append([InlineKeyboardButton(
                text="📚 Перейти к курсу",
                callback_data=f"course_{guide['related_course_slug']}"
            )])
        
        # Кнопки навигации - используем back_navigation для возврата
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Отправляем файл гайда с кнопками
        await callback.message.answer_document(
            document=file_id,
            caption=f"✅ **Оплата успешна!**\n\n{guide.get('emoji') or '💝'} Ваш {guide['name']} готов!\n\nЖелаем вам успехов в изучении! 🌟",
            parse_mode="Markdown",
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

"""
Обработчик вебхуков от YooKassa для автоматической обработки платежей
"""
import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_db, PaymentRepository, UserRepository
from data import get_course_by_slug, get_consultation_by_slug, get_guide_by_id, get_tariff_by_id
from payments import YooKassaPayment
from config import config

logger = logging.getLogger(__name__)


async def process_payment_webhook(
    notification_data: Dict[str, Any], 
    bot: Bot
) -> bool:
    """
    Обработка уведомления от YooKassa о статусе платежа
    
    Args:
        notification_data: Данные уведомления от YooKassa
        bot: Экземпляр бота для отправки сообщений
        
    Returns:
        bool: Успешность обработки
    """
    try:
        # Парсим уведомление
        notification = YooKassaPayment.parse_webhook_notification(notification_data)
        
        if not notification:
            logger.error("Failed to parse webhook notification")
            return False
        
        # Получаем объект платежа из уведомления
        payment_obj = notification.object
        payment_id = payment_obj.id
        payment_status = payment_obj.status
        
        logger.info(f"Processing webhook for payment {payment_id}, status: {payment_status}")
        
        # Находим платеж в нашей базе данных
        db = await get_db()
        payment_repo = PaymentRepository(db)
        
        payment = await payment_repo.get_by_payment_id(payment_id)
        
        if not payment:
            logger.warning(f"Payment {payment_id} not found in database")
            return False
        
        # Обрабатываем успешный платеж
        if payment_status == 'succeeded' and payment['status'] != 'succeeded':
            await payment_repo.update_status(payment_id, 'succeeded')
            
            logger.info(f"Payment {payment_id} marked as succeeded")
            
            # Отправляем уведомление пользователю
            await notify_user_payment_success(bot, payment, db)
            
            # Уведомляем админа
            await notify_admin_new_payment(bot, payment, db)
            
            return True
        
        # Обрабатываем отмененный/неуспешный платеж
        elif payment_status in ['canceled', 'failed']:
            await payment_repo.update_status(payment_id, payment_status)
            
            logger.info(f"Payment {payment_id} marked as {payment_status}")
            return True
        
        return True
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return False


async def notify_user_payment_success(bot: Bot, payment: dict, db):
    """
    Отправка уведомления пользователю об успешной оплате
    
    Args:
        bot: Экземпляр бота
        payment: Объект платежа из БД (dict)
        db: База данных
    """
    try:
        # Получаем пользователя как dict
        user_data = await db.users.find_one({"_id": payment['user_id']})
        
        if not user_data:
            logger.warning(f"User not found for payment {payment['_id']}")
            return
        
        # Формируем сообщение в зависимости от типа продукта
        if payment['product_type'] in ['course', 'mini_course']:
            await notify_course_payment(bot, user_data, payment)
        elif payment['product_type'] == 'consultation':
            await notify_consultation_payment(bot, user_data, payment)
        elif payment['product_type'] == 'guide':
            await notify_guide_payment(bot, user_data, payment)
        else:
            # Общее уведомление
            await bot.send_message(
                chat_id=user_data['telegram_id'],
                text="✅ <b>Оплата успешна!</b>\n\nСпасибо за покупку! 🌟"
            )
    
    except Exception as e:
        logger.error(f"Error notifying user about payment: {e}", exc_info=True)


async def notify_course_payment(bot: Bot, user: dict, payment: dict):
    """Уведомление об оплате курса или мини-курса"""
    course_slug = payment.get('course_slug')
    
    # Определяем, это мини-курс или обычный курс
    if course_slug == 'mini_course':
        from data import get_mini_course, get_mini_course_tariff
        mini_course = get_mini_course()
        tariff = get_mini_course_tariff(payment.get('tariff_id')) if mini_course else None
        
        if not mini_course:
            logger.warning("Mini course not found")
            return
        
        text = f"🎉 <b>Поздравляем с покупкой!</b>\n\n"
        text += f"Вам открыт доступ к мини-курсу «{mini_course.get('title', 'Мини-курс')}»\n\n"
        
        if tariff and tariff.get('with_support'):
            text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
        
        text += "📚 Материалы курса доступны в вашем кабинете!"
    else:
        # Обычный курс
        course = get_course_by_slug(course_slug)
        tariff = get_tariff_by_id(course_slug, payment.get('tariff_id')) if course else None
        
        if not course:
            logger.warning(f"Course {course_slug} not found")
            return
        
        text = f"🎉 <b>Поздравляем с покупкой!</b>\n\n"
        text += f"Вам открыт доступ к курсу «{course['name']}»\n\n"
        
        if tariff and tariff.get('with_support'):
            text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
        
        text += "📚 Материалы курса доступны в вашем кабинете!"
    
    # Только кнопка "Мои курсы"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")]
    ])
    
    # Если есть chat_id и message_id - редактируем сообщение, иначе отправляем новое
    if payment.get('chat_id') and payment.get('message_id'):
        try:
            await bot.edit_message_text(
                chat_id=payment['chat_id'],
                message_id=payment['message_id'],
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to edit message, sending new one: {e}")
            # Если не удалось отредактировать - отправляем новое
            await bot.send_message(
                chat_id=user['telegram_id'],
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    else:
        # Для старых платежей без сохраненных chat_id/message_id
        await bot.send_message(
            chat_id=user['telegram_id'],
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


async def notify_consultation_payment(bot: Bot, user: dict, payment: dict):
    """Уведомление об оплате консультации"""
    consultation = get_consultation_by_slug(payment.get('consultation_slug'))
    
    if not consultation:
        logger.warning(f"Consultation {payment.get('consultation_slug')} not found")
        return
    
    text = "✅ <b>Оплата успешна!</b>\n\n"
    text += f"{consultation.get('emoji', '🔮')} Консультация «{consultation['name']}» оплачена!\n\n"
    text += "📞 В ближайшее время с вами свяжется астролог для согласования времени встречи.\n\n"
    text += "Спасибо за доверие! 🌟"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await bot.send_message(
        chat_id=user['telegram_id'],
        text=text,
        reply_markup=keyboard
    )


async def notify_guide_payment(bot: Bot, user: dict, payment: dict):
    """Уведомление об оплате гайда и отправка файла"""
    guide = get_guide_by_id(payment.get('product_id'))
    
    if not guide:
        logger.warning(f"Guide {payment.get('product_id')} not found")
        await bot.send_message(
            chat_id=user['telegram_id'],
            text="✅ <b>Оплата успешна!</b>\n\nГайд будет отправлен вам в течение нескольких минут."
        )
        return
    
    file_id = guide.get('file_id')
    
    if file_id:
        # Кнопки навигации
        buttons = []
        
        if guide.get('related_course_slug'):
            course = get_course_by_slug(guide['related_course_slug'])
            if course:
                button_text = f"{course.get('emoji', '📚')} Курс «{course['name']}»"
            else:
                button_text = "📚 Перейти к курсу"
            
            buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"course_{guide['related_course_slug']}"
            )])
        
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Отправляем файл с кнопками
        await bot.send_document(
            chat_id=user['telegram_id'],
            document=file_id,
            caption=f"✅ <b>Оплата успешна!</b>\n\n{guide.get('emoji', '💝')} Ваш {guide['name']} готов!\n\nЖелаем вам успехов в изучении! 🌟",
            reply_markup=keyboard
        )
    else:
        await bot.send_message(
            chat_id=user['telegram_id'],
            text="✅ <b>Оплата успешна!</b>\n\nГайд будет отправлен вам в течение нескольких минут."
        )


async def notify_admin_new_payment(bot: Bot, payment: dict, db):
    """
    Уведомление админа о новом платеже
    
    Args:
        bot: Экземпляр бота
        payment: Объект платежа (dict)
        db: База данных
    """
    try:
        if not config.ADMIN_ID:
            return
        
        # Получаем пользователя как dict
        user = await db.users.find_one({"_id": payment['user_id']})
        
        if not user:
            logger.warning(f"User not found for admin notification")
            return
        
        text = "🔔 <b>Новый платеж!</b>\n\n"
        
        # Информация о пользователе
        user_info = user.get('first_name', '') or ""
        if user.get('last_name'):
            user_info += f" {user['last_name']}"
        if user.get('username'):
            user_info += f" (@{user['username']})"
        if not user_info.strip():
            user_info = "Не указано"
        
        text += f"👤 Пользователь: {user_info}\n"
        text += f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        text += f"💰 Сумма: {payment['amount']:,.0f} ₽\n"
        
        # Показываем, если оплата была по ссылке
        if payment.get('is_payment_link'):
            text += f"🔗 <b>Оплата по сгенерированной ссылке</b>\n"
        
        text += f"📦 Тип: {payment['product_type']}\n"
        
        if payment['product_type'] == 'course':
            course = get_course_by_slug(payment.get('course_slug'))
            if course:
                text += f"📚 Курс: {course['name']}\n"
                tariff = get_tariff_by_id(payment.get('course_slug'), payment.get('tariff_id')) if payment.get('tariff_id') else None
                if tariff:
                    text += f"   Тариф: {tariff.get('name', 'Не указан')}\n"
        elif payment['product_type'] == 'consultation':
            consultation = get_consultation_by_slug(payment.get('consultation_slug'))
            if consultation:
                text += f"🔮 Консультация: {consultation['name']}\n"
                # Ищем опцию консультации
                if payment.get('consultation_option_id'):
                    options = consultation.get('options', [])
                    option = next((opt for opt in options if opt.get('id') == payment['consultation_option_id']), None)
                    if option:
                        text += f"   Опция: {option.get('name', 'Не указана')}\n"
        elif payment['product_type'] == 'guide':
            guide = get_guide_by_id(payment.get('product_id'))
            if guide:
                text += f"📖 Гайд: {guide['name']}\n"
        
        text += f"\n🆔 ID платежа: <code>{payment.get('payment_id')}</code>"
        paid_at = payment.get('paid_at')
        if paid_at:
            text += f"\n📅 Дата: {paid_at.strftime('%d.%m.%Y %H:%M')}"
        else:
            text += f"\n📅 Дата: Только что"
        
        # Добавляем кнопку для быстрого доступа к чату с пользователем (если есть username)
        keyboard = None
        if user.get('username'):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Написать пользователю", url=f"https://t.me/{user['username']}")]
            ])
        
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=text,
            reply_markup=keyboard
        )
    
    except Exception as e:
        logger.error(f"Error notifying admin: {e}", exc_info=True)


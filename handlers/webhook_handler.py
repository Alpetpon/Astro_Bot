"""
Обработчик вебхуков от YooKassa для автоматической обработки платежей
"""
import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_db, Payment
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
        db = get_db()
        try:
            payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
            
            if not payment:
                logger.warning(f"Payment {payment_id} not found in database")
                return False
            
            # Обрабатываем успешный платеж
            if payment_status == 'succeeded' and payment.status != 'succeeded':
                payment.status = 'succeeded'
                payment.paid_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Payment {payment_id} marked as succeeded")
                
                # Отправляем уведомление пользователю
                await notify_user_payment_success(bot, payment, db)
                
                # Уведомляем админа
                await notify_admin_new_payment(bot, payment, db)
                
                return True
            
            # Обрабатываем отмененный/неуспешный платеж
            elif payment_status in ['canceled', 'failed']:
                payment.status = payment_status
                db.commit()
                
                logger.info(f"Payment {payment_id} marked as {payment_status}")
                return True
            
            return True
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return False


async def notify_user_payment_success(bot: Bot, payment: Payment, db):
    """
    Отправка уведомления пользователю об успешной оплате
    
    Args:
        bot: Экземпляр бота
        payment: Объект платежа из БД
        db: Сессия базы данных
    """
    try:
        user = payment.user
        
        if not user:
            logger.warning(f"User not found for payment {payment.id}")
            return
        
        # Формируем сообщение в зависимости от типа продукта
        if payment.product_type == 'course':
            await notify_course_payment(bot, user, payment)
        elif payment.product_type == 'consultation':
            await notify_consultation_payment(bot, user, payment)
        elif payment.product_type == 'guide':
            await notify_guide_payment(bot, user, payment)
        else:
            # Общее уведомление
            await bot.send_message(
                chat_id=user.telegram_id,
                text="✅ <b>Оплата успешна!</b>\n\nСпасибо за покупку! 🌟"
            )
    
    except Exception as e:
        logger.error(f"Error notifying user about payment: {e}", exc_info=True)


async def notify_course_payment(bot: Bot, user, payment: Payment):
    """Уведомление об оплате курса"""
    course = get_course_by_slug(payment.course_slug)
    tariff = get_tariff_by_id(payment.course_slug, payment.tariff_id) if course else None
    
    if not course:
        logger.warning(f"Course {payment.course_slug} not found")
        return
    
    text = "✅ <b>Оплата успешна!</b>\n\n"
    text += f"Вам открыт доступ к курсу «{course['name']}»\n\n"
    
    if tariff and tariff.get('with_support'):
        text += "👨‍🏫 В ближайшее время с вами свяжется куратор.\n\n"
    
    text += "📚 Материалы курса скоро будут доступны в вашем кабинете!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Мои курсы", callback_data="cabinet")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await bot.send_message(
        chat_id=user.telegram_id,
        text=text,
        reply_markup=keyboard
    )


async def notify_consultation_payment(bot: Bot, user, payment: Payment):
    """Уведомление об оплате консультации"""
    consultation = get_consultation_by_slug(payment.consultation_slug)
    
    if not consultation:
        logger.warning(f"Consultation {payment.consultation_slug} not found")
        return
    
    text = "✅ <b>Оплата успешна!</b>\n\n"
    text += f"{consultation.get('emoji', '🔮')} Консультация «{consultation['name']}» оплачена!\n\n"
    text += "📞 В ближайшее время с вами свяжется астролог для согласования времени встречи.\n\n"
    text += "Спасибо за доверие! 🌟"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await bot.send_message(
        chat_id=user.telegram_id,
        text=text,
        reply_markup=keyboard
    )


async def notify_guide_payment(bot: Bot, user, payment: Payment):
    """Уведомление об оплате гайда и отправка файла"""
    guide = get_guide_by_id(payment.product_id)
    
    if not guide:
        logger.warning(f"Guide {payment.product_id} not found")
        await bot.send_message(
            chat_id=user.telegram_id,
            text="✅ <b>Оплата успешна!</b>\n\nГайд будет отправлен вам в течение нескольких минут."
        )
        return
    
    file_id = guide.get('file_id')
    
    if file_id:
        # Отправляем файл
        await bot.send_document(
            chat_id=user.telegram_id,
            document=file_id,
            caption=f"✅ <b>Оплата успешна!</b>\n\n{guide.get('emoji', '💝')} Ваш {guide['name']} готов!\n\nЖелаем вам успехов в изучении! 🌟"
        )
        
        # Кнопки навигации
        buttons = []
        
        if guide.get('related_course_slug'):
            buttons.append([InlineKeyboardButton(
                text="📚 Перейти к курсу",
                callback_data=f"course_{guide['related_course_slug']}"
            )])
        
        buttons.append([
            InlineKeyboardButton(text="◀️ К гайдам", callback_data="guides_list"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await bot.send_message(
            chat_id=user.telegram_id,
            text="Приятного изучения! 📖",
            reply_markup=keyboard
        )
    else:
        await bot.send_message(
            chat_id=user.telegram_id,
            text="✅ <b>Оплата успешна!</b>\n\nГайд будет отправлен вам в течение нескольких минут."
        )


async def notify_admin_new_payment(bot: Bot, payment: Payment, db):
    """
    Уведомление админа о новом платеже
    
    Args:
        bot: Экземпляр бота
        payment: Объект платежа
        db: Сессия базы данных
    """
    try:
        if not config.ADMIN_ID:
            return
        
        user = payment.user
        
        text = "🔔 <b>Новый платеж!</b>\n\n"
        text += f"👤 Пользователь: {user.full_name or 'Не указано'}\n"
        text += f"💰 Сумма: {payment.amount:,.0f} ₽\n"
        text += f"📦 Тип: {payment.product_type}\n"
        
        if payment.product_type == 'course':
            course = get_course_by_slug(payment.course_slug)
            if course:
                text += f"📚 Курс: {course['name']}\n"
        elif payment.product_type == 'consultation':
            consultation = get_consultation_by_slug(payment.consultation_slug)
            if consultation:
                text += f"🔮 Консультация: {consultation['name']}\n"
        elif payment.product_type == 'guide':
            guide = get_guide_by_id(payment.product_id)
            if guide:
                text += f"📖 Гайд: {guide['name']}\n"
        
        text += f"\n🆔 ID платежа: <code>{payment.payment_id}</code>"
        
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=text
        )
    
    except Exception as e:
        logger.error(f"Error notifying admin: {e}", exc_info=True)


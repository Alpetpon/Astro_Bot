"""
Обработчики для подписки на канал
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import config
from keyboards.keyboards import (
    get_subscription_channel_keyboard,
    get_subscription_payment_keyboard,
    get_subscription_status_keyboard
)

logger = logging.getLogger(__name__)

router = Router()

# Глобальные переменные для сервисов (будут инициализированы в bot.py)
subscription_service = None
payment_service = None


def init_services(sub_service, pay_service):
    """Инициализация сервисов"""
    global subscription_service, payment_service
    subscription_service = sub_service
    payment_service = pay_service


@router.callback_query(F.data == "subscription_channel")
async def show_subscription_channel(callback: CallbackQuery):
    """Показать информацию о канале с подпиской"""
    try:
        # Проверяем наличие активной подписки
        has_subscription = False
        if subscription_service:
            subscription = await subscription_service.get_active_subscription(callback.from_user.id)
            has_subscription = subscription is not None
        
        # Формируем текст
        text = config.SUBSCRIPTION_CHANNEL_TEXT
        text += f"\n\n💰 **Стоимость:** {config.SUBSCRIPTION_PRICE} ₽"
        text += f"\n📅 **Срок действия:** {config.SUBSCRIPTION_DAYS} дней"
        
        if has_subscription:
            text += "\n\n✅ У вас есть активная подписка!"
        
        # Показываем информацию с кнопками
        try:
            if callback.message.video:
                await callback.message.delete()
                await callback.bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=text,
                    reply_markup=get_subscription_channel_keyboard(has_subscription),
                    parse_mode="Markdown"
                )
            else:
                await callback.message.edit_text(
                    text,
                    reply_markup=get_subscription_channel_keyboard(has_subscription),
                    parse_mode="Markdown"
                )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_subscription_channel_keyboard(has_subscription),
                parse_mode="Markdown"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing subscription channel: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "subscription_buy")
async def buy_subscription(callback: CallbackQuery):
    """Создать платеж для покупки подписки"""
    try:
        if not payment_service or not subscription_service:
            await callback.answer("Сервис временно недоступен", show_alert=True)
            return
        
        # Проверяем, есть ли уже активная подписка
        subscription = await subscription_service.get_active_subscription(callback.from_user.id)
        if subscription:
            await callback.answer("У вас уже есть активная подписка!", show_alert=True)
            return
        
        # Создаем платеж через YooKassa
        payment_data = payment_service.create_payment(
            user_id=callback.from_user.id,
            return_url=f"https://t.me/{(await callback.bot.get_me()).username}"
        )
        
        # Сохраняем платеж в БД
        await subscription_service.save_payment(
            user_id=callback.from_user.id,
            payment_id=payment_data['payment_id'],
            amount=payment_data['amount'],
            currency=payment_data['currency'],
            status=payment_data['status']
        )
        
        # Формируем сообщение
        text = f"""💳 **Оплата подписки**

💰 Сумма: {payment_data['amount']} {payment_data['currency']}
📅 Срок: {config.SUBSCRIPTION_DAYS} дней

Для оплаты:
1. Нажмите кнопку "Оплатить"
2. Завершите оплату на странице YooKassa
3. Вернитесь в бот и нажмите "Проверить оплату"

После успешной оплаты вы получите уникальную ссылку для вступления в канал."""
        
        # Отправляем сообщение с кнопками
        await callback.message.edit_text(
            text,
            reply_markup=get_subscription_payment_keyboard(
                payment_data['confirmation_url'],
                payment_data['payment_id']
            ),
            parse_mode="Markdown"
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        await callback.answer("Ошибка при создании платежа. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("subscription_check_payment_"))
async def check_payment(callback: CallbackQuery):
    """Проверить статус платежа"""
    try:
        if not payment_service or not subscription_service:
            await callback.answer("Сервис временно недоступен", show_alert=True)
            return
        
        # Извлекаем payment_id из callback_data
        payment_id = callback.data.replace("subscription_check_payment_", "")
        
        # Проверяем статус в YooKassa
        payment_data = payment_service.check_payment(payment_id)
        
        # Обрабатываем статус
        if payment_data["status"] == "succeeded" and payment_data["paid"]:
            # Обновляем статус в БД
            await subscription_service.update_payment_status(
                payment_id=payment_id,
                status="succeeded",
                paid_at=datetime.utcnow()
            )
            
            # Создаем подписку
            subscription = await subscription_service.create_subscription(
                user_id=callback.from_user.id,
                payment_id=payment_id
            )
            
            # Связываем платеж с подпиской
            await subscription_service.link_payment_to_subscription(
                payment_id=payment_id,
                subscription_id=subscription['_id']
            )
            
            # Формируем сообщение с ссылкой
            end_date_str = subscription['end_date'].strftime('%d.%m.%Y %H:%M')
            
            text = f"""✅ **Оплата успешно завершена!**

🎉 Поздравляем! Ваша подписка активирована.

🔗 **Ваша персональная ссылка:**
{subscription['invite_link']}

📅 **Действует до:** {end_date_str}

💡 **Важно:**
• Ссылка работает только для вас
• Срок действия ограничен
• За 3 дня и за 1 день до окончания вы получите напоминание

Приятного использования! 🤍"""
            
            await callback.message.edit_text(
                text,
                reply_markup=get_subscription_status_keyboard(),
                parse_mode="Markdown"
            )
            
            await callback.answer("Подписка активирована! ✅")
            
        else:
            # Платеж не завершен
            status_message = payment_service.get_payment_status_message(
                payment_data["status"],
                payment_data["paid"]
            )
            
            await callback.answer(status_message, show_alert=True)
        
    except Exception as e:
        logger.error(f"Error checking payment: {e}")
        await callback.answer("Ошибка при проверке платежа. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "subscription_status")
async def show_subscription_status(callback: CallbackQuery):
    """Показать статус подписки"""
    try:
        if not subscription_service:
            await callback.answer("Сервис временно недоступен", show_alert=True)
            return
        
        # Получаем активную подписку
        subscription = await subscription_service.get_active_subscription(callback.from_user.id)
        
        if not subscription:
            text = """❌ **Подписка не найдена**

У вас нет активной подписки на канал.

Хотите оформить подписку?"""
            
            await callback.message.edit_text(
                text,
                reply_markup=get_subscription_channel_keyboard(False),
                parse_mode="Markdown"
            )
        else:
            # Форматируем даты
            end_date = subscription['end_date']
            now = datetime.utcnow()
            days_left = (end_date - now).days
            hours_left = ((end_date - now).seconds // 3600)
            
            end_date_str = end_date.strftime('%d.%m.%Y %H:%M')
            
            # Формируем сообщение
            text = f"""📊 **Статус подписки**

✅ Подписка активна

📅 **Дата окончания:** {end_date_str}
⏳ **Осталось:** {days_left} дн. {hours_left} ч.

🔗 **Ваша ссылка:**
{subscription['invite_link']}

💡 Вы получите напоминание за 3 дня и за 1 день до окончания."""
            
            # Можно продлить, если осталось меньше 7 дней
            can_renew = days_left < 7
            
            await callback.message.edit_text(
                text,
                reply_markup=get_subscription_status_keyboard(can_renew),
                parse_mode="Markdown"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing subscription status: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


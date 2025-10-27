"""
Обработчики для подписки на канал
"""
import logging
import re
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

from config import config
from keyboards.keyboards import (
    get_subscription_channel_keyboard,
    get_subscription_payment_keyboard,
    get_subscription_status_keyboard
)

logger = logging.getLogger(__name__)

router = Router()


class SubscriptionEmailStates(StatesGroup):
    """Состояния для запроса email при оплате подписки"""
    waiting_for_email = State()

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
async def buy_subscription(callback: CallbackQuery, state: FSMContext):
    """Запрос email для покупки подписки"""
    try:
        if not payment_service or not subscription_service:
            await callback.answer("Сервис временно недоступен", show_alert=True)
            return
        
        # Проверяем, есть ли уже активная подписка
        subscription = await subscription_service.get_active_subscription(callback.from_user.id)
        if subscription:
            await callback.answer("У вас уже есть активная подписка!", show_alert=True)
            return
        
        # Запрашиваем email
        await state.set_state(SubscriptionEmailStates.waiting_for_email)
        
        # Отправляем сообщение с запросом email
        try:
            await callback.message.edit_text(
                "📧 **Введите ваш email**\n\n"
                "На указанную почту будет отправлен чек об оплате.\n\n"
                "Пример: example@mail.ru",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_subscription_payment")]
                ])
            )
        except Exception:
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text="📧 **Введите ваш email**\n\n"
                     "На указанную почту будет отправлен чек об оплате.\n\n"
                     "Пример: example@mail.ru",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_subscription_payment")]
                ]),
                parse_mode="Markdown"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in buy_subscription: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "cancel_subscription_payment")
async def cancel_subscription_payment(callback: CallbackQuery, state: FSMContext):
    """Отмена оплаты подписки"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Оплата отменена.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="subscription_channel")]
        ])
    )
    await callback.answer()


@router.message(StateFilter(SubscriptionEmailStates.waiting_for_email))
async def process_subscription_email(message: Message, state: FSMContext):
    """Обработка введенного email и создание платежа для подписки"""
    email = message.text.strip()
    
    # Валидация email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        await message.answer(
            "❌ Неверный формат email. Пожалуйста, введите корректный email.\n\n"
            "Пример: example@mail.ru",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_subscription_payment")]
            ])
        )
        return
    
    try:
        if not payment_service or not subscription_service:
            await message.answer("❌ Сервис временно недоступен. Попробуйте позже.")
            await state.clear()
            return
        
        # Создаем платеж через YooKassa с email
        bot_info = await message.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_data = payment_service.create_payment(
            user_id=message.from_user.id,
            return_url=return_url,
            customer_email=email
        )
        
        # Сохраняем платеж в БД
        await subscription_service.save_payment(
            user_id=message.from_user.id,
            payment_id=payment_data['payment_id'],
            amount=payment_data['amount'],
            currency=payment_data['currency'],
            status=payment_data['status']
        )
        
        # Формируем сообщение
        text = f"""💳 **Оплата подписки**

💰 Сумма: {payment_data['amount']} {payment_data['currency']}
📅 Срок: {config.SUBSCRIPTION_DAYS} дней
📧 Email для чека: {email}

Для оплаты:
1. Нажмите кнопку "Оплатить"
2. Завершите оплату на странице YooKassa
3. Вернитесь в бот и нажмите "Проверить оплату"

После успешной оплаты вы получите уникальную ссылку для вступления в канал."""
        
        # Отправляем сообщение с кнопками
        await message.answer(
            text,
            reply_markup=get_subscription_payment_keyboard(
                payment_data['confirmation_url'],
                payment_data['payment_id']
            ),
            parse_mode="Markdown"
        )
        
        # Очищаем state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_subscription_email: {e}")
        await message.answer("❌ Ошибка при создании платежа. Попробуйте позже.")
        await state.clear()


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


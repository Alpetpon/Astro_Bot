"""
Планировщик задач для подписок на канал
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from config import config

logger = logging.getLogger(__name__)


async def check_expired_subscriptions(bot: Bot, subscription_service):
    """
    Проверить и обработать истекшие подписки
    
    Args:
        bot: Экземпляр бота
        subscription_service: Сервис управления подписками
    """
    try:
        logger.info("Checking expired subscriptions...")
        
        # Получаем истекшие подписки
        expired_subscriptions = await subscription_service.get_expired_subscriptions()
        
        for subscription in expired_subscriptions:
            user_id = subscription['user_id']
            end_date_str = subscription['end_date'].strftime('%d.%m.%Y %H:%M')
            
            logger.info(f"Processing expired subscription for user {user_id}")
            
            # Удаляем пользователя из канала
            kicked = await subscription_service.kick_user_from_channel(user_id)
            
            # Деактивируем подписку
            deactivated = await subscription_service.deactivate_subscription(subscription['_id'])
            
            if kicked and deactivated:
                # Отправляем уведомление пользователю
                try:
                    text = f"""⏰ **Ваша подписка истекла**

📅 Дата окончания: {end_date_str}

Вы были удалены из канала.
Чтобы продолжить, продлите подписку!"""
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="Markdown"
                    )
                    
                    logger.info(f"Notification sent to user {user_id}")
                    
                except Exception as e:
                    logger.error(f"Error sending notification to user {user_id}: {e}")
        
        logger.info(f"Processed {len(expired_subscriptions)} expired subscriptions")
        
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {e}")


async def notify_expiring_3_days(bot: Bot, subscription_service):
    """
    Уведомить пользователей за 3 дня до истечения подписки
    
    Args:
        bot: Экземпляр бота
        subscription_service: Сервис управления подписками
    """
    try:
        logger.info("Checking subscriptions expiring in 3 days...")
        
        # Получаем подписки, истекающие через 3 дня
        expiring_subscriptions = await subscription_service.get_expiring_subscriptions(days_before=3)
        
        for subscription in expiring_subscriptions:
            user_id = subscription['user_id']
            end_date_str = subscription['end_date'].strftime('%d.%m.%Y %H:%M')
            
            logger.info(f"Sending 3-day notification to user {user_id}")
            
            try:
                text = f"""⚠️ **Напоминание о подписке**

Ваша подписка истекает скоро!

📅 Дата окончания: {end_date_str}
⏳ Осталось: 3 дня

Не забудьте продлить доступ!"""
                
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="Markdown"
                )
                
                # Помечаем, что уведомление отправлено
                await subscription_service.mark_notification_sent(
                    subscription['_id'],
                    days_before=3
                )
                
                logger.info(f"3-day notification sent to user {user_id}")
                
            except Exception as e:
                logger.error(f"Error sending 3-day notification to user {user_id}: {e}")
        
        logger.info(f"Sent {len(expiring_subscriptions)} 3-day notifications")
        
    except Exception as e:
        logger.error(f"Error notifying expiring subscriptions (3 days): {e}")


async def notify_expiring_1_day(bot: Bot, subscription_service):
    """
    Уведомить пользователей за 1 день до истечения подписки
    
    Args:
        bot: Экземпляр бота
        subscription_service: Сервис управления подписками
    """
    try:
        logger.info("Checking subscriptions expiring in 1 day...")
        
        # Получаем подписки, истекающие через 1 день
        expiring_subscriptions = await subscription_service.get_expiring_subscriptions(days_before=1)
        
        for subscription in expiring_subscriptions:
            user_id = subscription['user_id']
            end_date_str = subscription['end_date'].strftime('%d.%m.%Y %H:%M')
            auto_renew = subscription.get('auto_renew', False)
            
            logger.info(f"Sending 1-day notification to user {user_id}, auto_renew={auto_renew}")
            
            try:
                if auto_renew:
                    text = f"""🔄 **Автопродление подписки**

Ваша подписка скоро продлится автоматически!

📅 Дата окончания текущего периода: {end_date_str}
💳 Завтра будет произведено списание {config.SUBSCRIPTION_PRICE:.0f}₽

Если хотите отменить автопродление, свяжитесь с поддержкой."""
                else:
                    text = f"""🔴 **Напоминание о подписке**

Ваша подписка истекает завтра!

📅 Дата окончания: {end_date_str}
⏳ Осталось: 1 день

Не забудьте продлить доступ!"""
                
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="Markdown"
                )
                
                # Помечаем, что уведомление отправлено
                await subscription_service.mark_notification_sent(
                    subscription['_id'],
                    days_before=1
                )
                
                logger.info(f"1-day notification sent to user {user_id}")
                
            except Exception as e:
                logger.error(f"Error sending 1-day notification to user {user_id}: {e}")
        
        logger.info(f"Sent {len(expiring_subscriptions)} 1-day notifications")
        
    except Exception as e:
        logger.error(f"Error notifying expiring subscriptions (1 day): {e}")


async def auto_renew_subscriptions(bot: Bot, subscription_service, yookassa_payment):
    """
    Автоматическое продление подписок с рекуррентными платежами
    
    Args:
        bot: Экземпляр бота
        subscription_service: Сервис управления подписками
        yookassa_payment: Сервис YooKassa для создания платежей
    """
    try:
        logger.info("Checking subscriptions for auto-renewal...")
        
        # Получаем подписки для автопродления
        subscriptions_to_renew = await subscription_service.get_subscriptions_to_renew()
        
        for subscription in subscriptions_to_renew:
            user_id = subscription['user_id']
            subscription_id = subscription['_id']
            payment_method_id = subscription.get('payment_method_id')
            
            logger.info(f"Attempting auto-renewal for user {user_id}, subscription {subscription_id}")
            
            # Помечаем попытку продления
            await subscription_service.mark_renewal_attempted(subscription_id)
            
            try:
                # Создаем рекуррентный платеж
                payment_result = yookassa_payment.create_recurrent_payment(
                    amount=config.SUBSCRIPTION_PRICE,
                    description="Автопродление подписки на канал",
                    payment_method_id=payment_method_id,
                    metadata={
                        "user_id": user_id,
                        "subscription_id": str(subscription_id),
                        "auto_renewal": True
                    }
                )
                
                if payment_result and payment_result['status'] == 'succeeded':
                    # Платеж прошел успешно - продлеваем подписку
                    extended = await subscription_service.extend_subscription(
                        subscription_id, 
                        payment_result['id']
                    )
                    
                    # Сохраняем платеж в БД
                    await subscription_service.save_payment(
                        user_id=user_id,
                        payment_id=payment_result['id'],
                        amount=payment_result['amount'],
                        status='succeeded'
                    )
                    
                    if extended:
                        # Уведомляем пользователя об успешном продлении
                        new_end_date = subscription['end_date']
                        from datetime import timedelta
                        new_end_date = new_end_date + timedelta(days=config.SUBSCRIPTION_DAYS)
                        
                        text = f"""✅ **Подписка успешно продлена!**

💳 Списано: {config.SUBSCRIPTION_PRICE:.0f}₽
📅 Подписка действует до: {new_end_date.strftime('%d.%m.%Y')}

Спасибо за то, что остаетесь с нами! 🌟"""
                        
                        await bot.send_message(
                            chat_id=user_id,
                            text=text,
                            parse_mode="Markdown"
                        )
                        
                        logger.info(f"Successfully renewed subscription for user {user_id}")
                    
                else:
                    # Платеж не прошел - удаляем из канала и деактивируем
                    logger.warning(f"Auto-renewal payment failed for user {user_id}")
                    
                    # Удаляем из канала
                    await subscription_service.kick_user_from_channel(user_id)
                    
                    # Деактивируем подписку
                    await subscription_service.deactivate_subscription(subscription_id)
                    
                    # Уведомляем пользователя
                    text = f"""❌ **Не удалось продлить подписку**

К сожалению, автоматическое списание не прошло.

💳 Сумма: {config.SUBSCRIPTION_PRICE:.0f}₽

Возможные причины:
• Недостаточно средств на карте
• Карта заблокирована
• Истек срок действия карты

Вы были удалены из канала. Чтобы восстановить доступ, оформите подписку заново."""
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="Markdown"
                    )
                    
                    logger.info(f"User {user_id} removed from channel due to failed payment")
                    
            except Exception as e:
                logger.error(f"Error processing auto-renewal for user {user_id}: {e}")
                
                # При ошибке удаляем из канала
                await subscription_service.kick_user_from_channel(user_id)
                await subscription_service.deactivate_subscription(subscription_id)
                
                # Уведомляем пользователя об ошибке
                try:
                    text = "❌ **Ошибка при продлении подписки**\n\nПроизошла ошибка при автоматическом продлении. Пожалуйста, оформите подписку заново."
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="Markdown"
                    )
                except:
                    pass
        
        logger.info(f"Processed {len(subscriptions_to_renew)} subscriptions for auto-renewal")
        
    except Exception as e:
        logger.error(f"Error in auto_renew_subscriptions: {e}")


def setup_subscription_scheduler(bot: Bot, subscription_service, yookassa_payment=None) -> AsyncIOScheduler:
    """
    Настроить планировщик задач для подписок
    
    Args:
        bot: Экземпляр бота
        subscription_service: Сервис управления подписками
        yookassa_payment: Сервис YooKassa (опционально, для автопродления)
        
    Returns:
        Экземпляр планировщика
    """
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # Проверка истекших подписок - каждый час
    scheduler.add_job(
        check_expired_subscriptions,
        "interval",
        hours=1,
        args=[bot, subscription_service],
        id="check_expired_subscriptions",
        replace_existing=True
    )
    logger.info("✅ Scheduled: check_expired_subscriptions (every hour)")
    
    # Уведомления за 3 дня - каждые 6 часов
    scheduler.add_job(
        notify_expiring_3_days,
        "interval",
        hours=6,
        args=[bot, subscription_service],
        id="notify_expiring_3_days",
        replace_existing=True
    )
    logger.info("✅ Scheduled: notify_expiring_3_days (every 6 hours)")
    
    # Уведомления за 1 день - каждые 3 часа
    scheduler.add_job(
        notify_expiring_1_day,
        "interval",
        hours=3,
        args=[bot, subscription_service],
        id="notify_expiring_1_day",
        replace_existing=True
    )
    logger.info("✅ Scheduled: notify_expiring_1_day (every 3 hours)")
    
    # Автопродление подписок - каждые 2 часа
    if yookassa_payment:
        scheduler.add_job(
            auto_renew_subscriptions,
            "interval",
            hours=2,
            args=[bot, subscription_service, yookassa_payment],
            id="auto_renew_subscriptions",
            replace_existing=True
        )
        logger.info("✅ Scheduled: auto_renew_subscriptions (every 2 hours)")
    
    return scheduler


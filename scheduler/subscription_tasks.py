"""
Планировщик задач для подписок на канал
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

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
            
            logger.info(f"Sending 1-day notification to user {user_id}")
            
            try:
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


def setup_subscription_scheduler(bot: Bot, subscription_service) -> AsyncIOScheduler:
    """
    Настроить планировщик задач для подписок
    
    Args:
        bot: Экземпляр бота
        subscription_service: Сервис управления подписками
        
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
    
    return scheduler


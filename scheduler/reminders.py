from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy import and_
from sqlalchemy.orm import Session

from config import config
from database import get_db, User, UserProgress, Payment


async def check_inactive_users(bot: Bot):
    """Проверка неактивных пользователей и отправка напоминаний"""
    db: Session = get_db()
    
    try:
        # Вычисляем дату отсечения (3 дня назад)
        cutoff_date = datetime.utcnow() - timedelta(days=config.INACTIVITY_DAYS)
        
        # Находим пользователей, которые были активны более 3 дней назад
        inactive_users = db.query(User).filter(
            and_(
                User.last_activity < cutoff_date,
                User.is_active == True
            )
        ).all()
        
        for user in inactive_users:
            # Проверяем, есть ли у пользователя купленные курсы
            has_courses = db.query(Payment).filter(
                Payment.user_id == user.id,
                Payment.status == 'succeeded'
            ).count() > 0
            
            if not has_courses:
                continue
            
            # Проверяем, есть ли незавершенные уроки
            has_incomplete = db.query(UserProgress).filter(
                and_(
                    UserProgress.user_id == user.id,
                    UserProgress.is_available == True,
                    UserProgress.is_completed == False
                )
            ).count() > 0
            
            if has_incomplete:
                # Отправляем напоминание
                try:
                    message = (
                        "👋 Привет!\n\n"
                        "Заметили, что вы давно не заходили на курс.\n"
                        "У вас есть доступные уроки для изучения! 📚\n\n"
                        "Продолжайте обучение, чтобы достичь лучших результатов! ✨\n\n"
                        "Нажмите /start для входа в бот."
                    )
                    
                    await bot.send_message(user.telegram_id, message)
                    print(f"Reminder sent to user {user.telegram_id}")
                
                except Exception as e:
                    print(f"Error sending reminder to user {user.telegram_id}: {e}")
    
    except Exception as e:
        print(f"Error in check_inactive_users: {e}")
    
    finally:
        db.close()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Настройка планировщика задач"""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Проверка неактивных пользователей каждый день в 12:00
    scheduler.add_job(
        check_inactive_users,
        'cron',
        hour=12,
        minute=0,
        args=[bot]
    )
    
    # Можно добавить другие задачи
    # Например, напоминание о предстоящих вебинарах и т.д.
    
    return scheduler


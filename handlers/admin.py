from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import config
from database import get_db, User, Payment, Course, Consultation
from keyboards import get_admin_keyboard, get_back_to_admin_keyboard

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id == config.ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Вход в админ-панель по команде /admin"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Показать админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        # Общая статистика
        total_users = db.query(User).count()
        total_purchases = db.query(Payment).count()
        total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0
        
        # Активные пользователи (за последние 7 дней)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users = db.query(User).filter(User.last_activity >= week_ago).count()
        
        # Новые пользователи за неделю
        new_users = db.query(User).filter(User.created_at >= week_ago).count()
        
        # Покупки за неделю
        week_purchases = db.query(Payment).filter(Payment.created_at >= week_ago).count()
        week_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.created_at >= week_ago
        ).scalar() or 0
        
        # Курсы и консультации
        total_courses = db.query(Course).count()
        total_consultations = db.query(Consultation).count()
        
        stats_text = f"""📊 <b>Статистика</b>

👥 <b>Пользователи:</b>
• Всего: {total_users}
• Активных за неделю: {active_users}
• Новых за неделю: {new_users}

💰 <b>Финансы:</b>
• Всего покупок: {total_purchases}
• Общая выручка: {total_revenue:,.0f} ₽
• За неделю покупок: {week_purchases}
• За неделю выручка: {week_revenue:,.0f} ₽

📚 <b>Контент:</b>
• Курсов: {total_courses}
• Консультаций: {total_consultations}
"""
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_to_admin_keyboard()
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def show_users(callback: CallbackQuery):
    """Показать последних пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        # Последние 10 пользователей
        users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
        
        users_text = "👥 <b>Последние пользователи:</b>\n\n"
        
        for user in users:
            username = f"@{user.username}" if user.username else "Без username"
            name = user.first_name or "Без имени"
            
            # Количество покупок
            purchases_count = len(user.payments)
            
            users_text += f"• {name} ({username})\n"
            users_text += f"  ID: <code>{user.telegram_id}</code>\n"
            users_text += f"  Покупок: {purchases_count}\n"
            users_text += f"  Регистрация: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        
        await callback.message.edit_text(
            users_text,
            reply_markup=get_back_to_admin_keyboard()
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "admin_purchases")
async def show_purchases(callback: CallbackQuery):
    """Показать последние покупки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        # Последние 10 покупок
        purchases = db.query(Payment).order_by(Payment.created_at.desc()).limit(10).all()
        
        if not purchases:
            purchases_text = "📦 <b>Покупки отсутствуют</b>"
        else:
            purchases_text = "📦 <b>Последние покупки:</b>\n\n"
            
            for purchase in purchases:
                user = purchase.user
                username = f"@{user.username}" if user.username else "Без username"
                name = user.first_name or "Без имени"
                
                # Тип покупки
                item_type = "Курс" if purchase.course_id else "Консультация"
                item_name = ""
                if purchase.course_id:
                    course = db.query(Course).filter(Course.id == purchase.course_id).first()
                    item_name = course.name if course else "Неизвестно"
                elif purchase.consultation_id:
                    consultation = db.query(Consultation).filter(
                        Consultation.id == purchase.consultation_id
                    ).first()
                    item_name = consultation.name if consultation else "Неизвестно"
                
                purchases_text += f"• {name} ({username})\n"
                purchases_text += f"  {item_type}: {item_name}\n"
                purchases_text += f"  Сумма: {purchase.amount:,.0f} ₽\n"
                purchases_text += f"  Дата: {purchase.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        await callback.message.edit_text(
            purchases_text,
            reply_markup=get_back_to_admin_keyboard()
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def broadcast_info(callback: CallbackQuery):
    """Информация о рассылке"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Для отправки рассылки всем пользователям используйте команду:\n"
        "<code>/broadcast [текст сообщения]</code>\n\n"
        "Пример:\n"
        "<code>/broadcast Новый курс уже доступен!</code>",
        reply_markup=get_back_to_admin_keyboard()
    )
    await callback.answer()


@router.message(Command("broadcast"))
async def broadcast_message(message: Message):
    """Рассылка сообщения всем пользователям"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    # Получаем текст сообщения
    text = message.text.replace("/broadcast", "").strip()
    
    if not text:
        await message.answer(
            "❌ Укажите текст сообщения:\n"
            "<code>/broadcast [текст]</code>"
        )
        return
    
    db: Session = get_db()
    
    try:
        # Получаем всех пользователей
        users = db.query(User).all()
        
        success_count = 0
        fail_count = 0
        
        status_msg = await message.answer(f"📤 Начинаю рассылку для {len(users)} пользователей...")
        
        for user in users:
            try:
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=text
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
        
        await status_msg.edit_text(
            f"✅ Рассылка завершена!\n\n"
            f"Успешно: {success_count}\n"
            f"Ошибок: {fail_count}"
        )
    
    finally:
        db.close()


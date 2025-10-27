"""
Административные функции для управления подписками
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from utils.bot_settings import is_admin
from keyboards.keyboards import get_admin_subscriptions_keyboard

logger = logging.getLogger(__name__)

router = Router()

# Глобальная переменная для сервиса (будет инициализирована в bot.py)
subscription_service = None


def init_service(service):
    """Инициализация сервиса"""
    global subscription_service
    subscription_service = service


@router.callback_query(F.data == "admin_subscriptions")
async def show_subscriptions_management(callback: CallbackQuery):
    """Показать меню управления подписками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    text = """💫 <b>Управление подписками</b>

Здесь вы можете управлять подписками пользователей на канал.

Выберите действие:"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_subscriptions_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_subscriptions_stats")
async def show_subscriptions_stats(callback: CallbackQuery):
    """Показать детальную статистику подписок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if not subscription_service:
        await callback.answer("Сервис подписок недоступен", show_alert=True)
        return
    
    try:
        # Получаем статистику
        stats = await subscription_service.get_subscription_stats()
        
        text = f"""📊 <b>Статистика подписок</b>

📋 <b>Подписки:</b>
• Всего подписок: {stats['total_subscriptions']}
• Активных подписок: {stats['active_subscriptions']}

💳 <b>Платежи:</b>
• Всего платежей: {stats['total_payments']}
• Успешных платежей: {stats['succeeded_payments']}
• Процент успеха: {(stats['succeeded_payments'] / stats['total_payments'] * 100) if stats['total_payments'] > 0 else 0:.1f}%

💰 <b>Финансы:</b>
• Общая сумма: {stats['total_amount']:,.2f} ₽
• Средний чек: {(stats['total_amount'] / stats['succeeded_payments']) if stats['succeeded_payments'] > 0 else 0:.2f} ₽"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscriptions")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing subscriptions stats: {e}")
        await callback.answer("Ошибка при получении статистики", show_alert=True)


@router.callback_query(F.data == "admin_subscriptions_clear")
async def confirm_clear_subscriptions(callback: CallbackQuery):
    """Запросить подтверждение очистки подписок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    text = """⚠️ <b>ВНИМАНИЕ!</b>

Вы собираетесь <b>полностью удалить</b> все данные о подписках:
• Все записи о подписках
• Все платежи за подписки

⚠️ <b>Это действие необратимо!</b>

Пользователи НЕ будут удалены из канала автоматически.

Вы уверены?"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА, ОЧИСТИТЬ ВСЁ", callback_data="admin_subscriptions_clear_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscriptions")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_subscriptions_clear_confirm")
async def clear_subscriptions_confirmed(callback: CallbackQuery):
    """Очистить все подписки после подтверждения"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        from database.mongodb import mongodb
        db = mongodb.get_database()
        
        # Удаляем все подписки
        result_subscriptions = await db.subscriptions.delete_many({})
        
        # Удаляем все платежи за подписки
        result_payments = await db.subscription_payments.delete_many({})
        
        text = f"""✅ <b>База данных очищена</b>

Удалено:
• Подписок: {result_subscriptions.deleted_count}
• Платежей: {result_payments.deleted_count}

Все данные о подписках удалены."""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subscriptions")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("База данных подписок очищена")
        
        logger.info(f"Admin {callback.from_user.id} cleared subscription database")
        
    except Exception as e:
        logger.error(f"Error clearing subscriptions: {e}")
        await callback.answer("Ошибка при очистке базы данных", show_alert=True)


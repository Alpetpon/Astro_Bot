import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

from database import get_db, UserRepository, PaymentRepository
from keyboards import get_back_keyboard
from data import (
    get_course_by_slug, 
    get_consultation_by_slug,
    get_course_modules,
    get_module_by_id,
    get_lesson_by_id
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_cabinet")
async def show_my_cabinet(callback: CallbackQuery):
    """Показать личный кабинет - статистика покупок"""
    from config import config as bot_config
    from database.mongodb import mongodb
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        # Обновляем активность
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if user:
            await user_repo.update_activity(callback.from_user.id)
        
        # Проверяем платежи
        payments = await payment_repo.get_user_payments(user.id)
        # Фильтруем только успешные платежи
        payments = [p for p in payments if p.status == 'succeeded']
        
        # Считаем статистику
        courses_count = len([p for p in payments if p.product_type in ['course', 'mini_course']])
        consultations_count = len([p for p in payments if p.product_type == 'consultation'])
        guides_count = len([p for p in payments if p.product_type == 'guide'])
        total_spent = sum(p.amount for p in payments)
        
        # Формируем текст
        text = "<b>💼 Мой кабинет</b>\n\n"
        
        text += "<b>📊 Моя статистика:</b>\n"
        text += f"• Курсов: {courses_count}\n"
        text += f"• Консультаций: {consultations_count}\n"
        text += f"• Гайдов: {guides_count}\n\n"
        text += f"💰 Всего потрачено: {total_spent:,.0f} ₽\n\n"
        
        # Проверяем активную подписку на канал
        mongo_db = mongodb.get_database()
        active_subscription = await mongo_db.subscriptions.find_one({
            "user_id": callback.from_user.id,
            "is_active": True
        })
        
        # Создаём клавиатуру
        buttons = []
        
        # Если есть активная подписка - добавляем кнопку управления
        if active_subscription:
            buttons.append([InlineKeyboardButton(
                text="🔄 Управление подпиской",
                callback_data="manage_subscription"
            )])
        
        if payments:
            text += "<b>🛍 Мои покупки:</b>\n\n"
            
            # Группируем покупки по типу
            courses = [p for p in payments if p.product_type in ['course', 'mini_course']]
            consultations = [p for p in payments if p.product_type == 'consultation']
            
            if courses:
                text += "<b>📚 Курсы:</b>\n"
                for payment in courses:
                    # Проверяем, это мини-курс или обычный курс
                    if payment.course_slug == "mini_course":
                        from data import get_mini_course
                        mini_course = get_mini_course()
                        if mini_course:
                            course_name = mini_course.get('title', 'Мини-курс')
                            emoji = mini_course.get('emoji', '🌌')
                            paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                            text += f"• {emoji} {course_name}\n"
                            text += f"  Куплено: {paid_date}\n"
                    else:
                        course = get_course_by_slug(payment.course_slug)
                        if course:
                            course_name = course.get('name', payment.course_slug)
                            emoji = course.get('emoji', '📚')
                            paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                            text += f"• {emoji} {course_name}\n"
                            text += f"  Куплено: {paid_date}\n"
                
                text += "\n🎓 <b>Для изучения материалов нажмите кнопку ниже:</b>\n\n"
                
                # Добавляем кнопку для перехода в учебный бот
                buttons.append([InlineKeyboardButton(
                    text="🎓 Перейти к обучению",
                    url=f"https://t.me/{bot_config.LEARNING_BOT_USERNAME}"
                )])
            
            if consultations:
                text += "<b>🔮 Консультации:</b>\n"
                for payment in consultations:
                    consultation = get_consultation_by_slug(payment.consultation_slug)
                    if consultation:
                        consultation_name = consultation.get('name', payment.consultation_slug)
                        emoji = consultation.get('emoji', '🔮')
                        text += f"• {emoji} {consultation_name}\n"
                        paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                        text += f"  Оплачено: {paid_date}\n"
                text += "\n"
        else:
            text += "📚 У вас пока нет купленных курсов или консультаций.\n\n"
            text += "Перейдите в каталог, чтобы выбрать подходящий курс!"
            
            # Добавляем кнопки для перехода к каталогам
            buttons.append([InlineKeyboardButton(text="📚 Каталог курсов", callback_data="courses")])
            buttons.append([InlineKeyboardButton(text="🔮 Консультации", callback_data="consultations")])
            buttons.append([InlineKeyboardButton(text="💕 Гайды", callback_data="guides_list")])
        
        # Кнопка назад
        buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            # Если это видео - удаляем и отправляем новое сообщение
            if callback.message.video:
                await callback.message.delete()
                await callback.bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=text,
                    reply_markup=keyboard
                )
            else:
                # Если текст - редактируем
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard
                )
        except Exception as edit_error:
            # Если не можем отредактировать - удаляем и отправляем новое
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=keyboard
            )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_my_cabinet: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "my_courses")
async def show_my_courses(callback: CallbackQuery):
    """Перенаправление на личный кабинет (для совместимости)"""
    # Перенаправляем на my_cabinet
    await show_my_cabinet(callback)


@router.callback_query(F.data == "manage_subscription")
async def manage_subscription(callback: CallbackQuery):
    """Управление подпиской на канал"""
    from database.mongodb import mongodb
    from datetime import datetime
    
    try:
        mongo_db = mongodb.get_database()
        subscription = await mongo_db.subscriptions.find_one({
            "user_id": callback.from_user.id,
            "is_active": True
        })
        
        if not subscription:
            await callback.answer("Активная подписка не найдена", show_alert=True)
            return
        
        # Форматируем данные
        end_date = subscription['end_date']
        now = datetime.utcnow()
        days_left = (end_date - now).days
        end_date_str = end_date.strftime('%d.%m.%Y %H:%M')
        
        auto_renew = subscription.get('auto_renew', False)
        has_payment_method = subscription.get('payment_method_id') is not None
        
        # Формируем текст
        text = "<b>🔄 Управление подпиской</b>\n\n"
        text += f"📅 <b>Действует до:</b> {end_date_str}\n"
        text += f"⏳ <b>Осталось:</b> {days_left} дней\n\n"
        
        if auto_renew:
            text += "🔄 <b>Автопродление:</b> ✅ включено\n"
            text += "💳 Подписка будет автоматически продлена\n\n"
        else:
            text += "🔄 <b>Автопродление:</b> ❌ отключено\n\n"
        
        if has_payment_method:
            text += "💳 <b>Карта:</b> привязана\n\n"
        else:
            text += "💳 <b>Карта:</b> не привязана\n\n"
        
        text += "⚙️ <b>Настройки:</b>"
        
        # Формируем кнопки
        buttons = []
        
        if auto_renew:
            buttons.append([InlineKeyboardButton(
                text="❌ Отключить автопродление",
                callback_data="disable_auto_renew"
            )])
        
        if has_payment_method:
            buttons.append([InlineKeyboardButton(
                text="🗑 Отвязать карту",
                callback_data="unbind_card"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="◀️ Назад в кабинет",
            callback_data="my_cabinet"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in manage_subscription: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "disable_auto_renew")
async def disable_auto_renew(callback: CallbackQuery):
    """Отключить автопродление подписки"""
    from database.mongodb import mongodb
    
    try:
        mongo_db = mongodb.get_database()
        
        result = await mongo_db.subscriptions.update_one(
            {
                "user_id": callback.from_user.id,
                "is_active": True
            },
            {
                "$set": {"auto_renew": False}
            }
        )
        
        if result.modified_count > 0:
            await callback.answer("✅ Автопродление отключено", show_alert=True)
            # Обновляем экран управления подпиской
            await manage_subscription(callback)
        else:
            await callback.answer("Подписка не найдена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error in disable_auto_renew: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "unbind_card")
async def unbind_card(callback: CallbackQuery):
    """Отвязать карту (удалить payment_method_id)"""
    from database.mongodb import mongodb
    
    try:
        mongo_db = mongodb.get_database()
        
        result = await mongo_db.subscriptions.update_one(
            {
                "user_id": callback.from_user.id,
                "is_active": True
            },
            {
                "$set": {
                    "payment_method_id": None,
                    "auto_renew": False  # Автопродление тоже отключаем
                }
            }
        )
        
        if result.modified_count > 0:
            await callback.answer(
                "✅ Карта отвязана\nАвтопродление отключено",
                show_alert=True
            )
            # Обновляем экран управления подпиской
            await manage_subscription(callback)
        else:
            await callback.answer("Подписка не найдена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error in unbind_card: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


# Удалены хэндлеры для материалов курсов - они теперь в учебном боте (learning_bot.py)
# my_course_, module_, lesson_, download_lecture_, mini_module_, mini_lesson_

from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.orm import Session

from config import config
from database import get_db, User
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_guides_list_keyboard, get_guide_keyboard, get_about_me_keyboard

router = Router()


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    """Показать главное меню"""
    db: Session = get_db()
    
    try:
        # Обновляем активность пользователя
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
        await callback.message.edit_text(
            "🏠 **Главное меню**\n\nВыберите интересующий раздел:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data == "about_me")
async def show_about_me(callback: CallbackQuery):
    """Показать информацию о преподавателе с кнопками соц. сетей"""
    text = config.ABOUT_ME_TEXT + "\n\n📱 **Мои соц. сети:**"
    await callback.message.edit_text(
        text,
        reply_markup=get_about_me_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "about_me_2")
async def show_about_me_2(callback: CallbackQuery):
    """Показать информацию о преподавателе с текстовыми ссылками на соц. сети"""
    text = config.ABOUT_ME_TEXT + f"\n\n📱 **Мои соц. сети:**\n\n"
    text += f"📱 [Instagram]({config.INSTAGRAM_URL})\n"
    text += f"🎥 [YouTube]({config.YOUTUBE_URL})\n"
    text += f"💙 [ВКонтакте]({config.VK_URL})\n"
    text += f"✈️ [Telegram канал]({config.TELEGRAM_CHANNEL_URL})\n"
    text += f"📰 [Дзен]({config.DZEN_URL})"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("main_menu", "◀️ Назад в меню"),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data == "guides_list")
async def show_guides_list(callback: CallbackQuery):
    """Показать список всех гайдов"""
    text = "💕 **Гайды**\n\nВыберите интересующий гайд:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_guides_list_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("guide_"))
async def show_guide(callback: CallbackQuery):
    """Показать информацию о конкретном гайде"""
    guide_id = callback.data.replace("guide_", "")
    
    # Находим гайд в конфиге
    guide = next((g for g in config.GUIDES if g['id'] == guide_id), None)
    
    if not guide:
        await callback.answer("Гайд не найден", show_alert=True)
        return
    
    # Проверяем, есть ли у пользователя этот гайд (купил ли он его)
    db: Session = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        has_access = False
        
        if user:
            from database import Payment
            # Проверяем, есть ли успешная оплата этого конкретного гайда
            payment = db.query(Payment).filter(
                Payment.user_id == user.id,
                Payment.product_type == 'guide',
                Payment.product_id == guide_id,
                Payment.status == 'succeeded'
            ).first()
            
            if payment:
                has_access = True
        
        # Показываем кнопку скачать если есть доступ, иначе кнопку покупки
        has_file = has_access and guide.get('file_id')
        
        await callback.message.edit_text(
            guide['description'],
            reply_markup=get_guide_keyboard(guide_id, has_file),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("download_guide_"))
async def download_guide(callback: CallbackQuery):
    """Скачать гайд (если пользователь его купил)"""
    guide_id = callback.data.replace("download_guide_", "")
    
    # Находим гайд в конфиге
    guide = next((g for g in config.GUIDES if g['id'] == guide_id), None)
    
    if not guide:
        await callback.answer("Гайд не найден", show_alert=True)
        return
    
    db: Session = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        from database import Payment
        # Проверяем, купил ли пользователь этот конкретный гайд
        payment = db.query(Payment).filter(
            Payment.user_id == user.id,
            Payment.product_type == 'guide',
            Payment.product_id == guide_id,
            Payment.status == 'succeeded'
        ).first()
        
        if not payment:
            await callback.answer("У вас нет доступа к этому гайду", show_alert=True)
            return
        
        file_id = guide.get('file_id')
        
        if not file_id:
            await callback.answer("Файл гайда не настроен. Обратитесь к администратору.", show_alert=True)
            return
        
        # Отправляем файл
        await callback.message.answer_document(
            document=file_id,
            caption=f"📥 {guide['name']}\n\nСпасибо за покупку!"
        )
        await callback.answer("Гайд отправлен!")
    
    except Exception as e:
        await callback.answer(f"Ошибка при отправке: {str(e)}", show_alert=True)
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("buy_guide_"))
async def buy_guide(callback: CallbackQuery):
    """Обработка покупки гайда"""
    guide_id = callback.data.replace("buy_guide_", "")
    
    # Находим гайд в конфиге
    guide = next((g for g in config.GUIDES if g['id'] == guide_id), None)
    
    if not guide:
        await callback.answer("Гайд не найден", show_alert=True)
        return
    
    from payments import YooKassaPayment
    from database import User, Payment
    
    db: Session = get_db()
    
    try:
        # Получаем пользователя
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        # Создаем платеж для гайда (без привязки к курсу)
        payment = Payment(
            user_id=user.id,
            course_id=None,  # Гайд не является курсом
            tariff_id=None,
            amount=guide['price'],
            status='pending',
            product_type='guide',
            product_id=guide_id  # ID гайда для последующей отправки
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Создаем платеж в ЮKassa
        yookassa = YooKassaPayment()
        payment_data = yookassa.create_payment(
            amount=guide['price'],
            description=guide['name'],
            payment_id=payment.id
        )
        
        if payment_data and 'confirmation' in payment_data:
            # Сохраняем данные платежа
            payment.payment_id = payment_data['id']
            payment.confirmation_url = payment_data['confirmation']['confirmation_url']
            db.commit()
            
            # Отправляем сообщение с кнопкой оплаты
            from keyboards import get_payment_keyboard
            await callback.message.edit_text(
                f"💳 **Оплата {guide['name']}**\n\n"
                f"Сумма: {guide['price']} ₽\n\n"
                "Нажмите кнопку ниже для перехода к оплате.\n"
                "После успешной оплаты гайд будет автоматически отправлен вам.",
                reply_markup=get_payment_keyboard(payment.confirmation_url, payment.id),
                parse_mode="Markdown"
            )
        else:
            await callback.answer("Ошибка при создании платежа", show_alert=True)
            payment.status = 'canceled'
            db.commit()
    
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)
    
    finally:
        db.close()
    
    await callback.answer()


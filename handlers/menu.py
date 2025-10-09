from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.orm import Session

from config import config
from database import get_db, User
from keyboards import get_main_menu_keyboard, get_back_keyboard

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
    """Показать информацию о преподавателе"""
    await callback.message.edit_text(
        config.ABOUT_ME_TEXT,
        reply_markup=get_back_keyboard("main_menu", "◀️ Назад в меню"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "guide_relationships")
async def show_guide_relationships(callback: CallbackQuery):
    """Показать информацию о гайде по отношениям"""
    await callback.message.edit_text(
        config.GUIDE_RELATIONSHIPS_TEXT,
        reply_markup=get_back_keyboard("main_menu", "◀️ Назад в меню"),
        parse_mode="Markdown"
    )
    await callback.answer()


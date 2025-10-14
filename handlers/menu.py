from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session

from config import config
from database import get_db, User, Guide
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
    
    # Находим гайд в БД
    db = get_db()
    guide = db.query(Guide).filter(Guide.guide_id == guide_id, Guide.is_active == True).first()
    
    if not guide:
        await callback.answer("Гайд не найден", show_alert=True)
        return
    
    # Гайды бесплатные, проверяем наличие файла
    has_file = bool(guide.file_id)
    related_course_slug = guide.related_course_slug
    
    await callback.message.edit_text(
        guide.description or guide.name,
        reply_markup=get_guide_keyboard(guide_id, has_file, related_course_slug),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("download_guide_"))
async def download_guide(callback: CallbackQuery):
    """Скачать гайд (бесплатно)"""
    guide_id = callback.data.replace("download_guide_", "")
    
    # Находим гайд в БД
    db = get_db()
    guide = db.query(Guide).filter(Guide.guide_id == guide_id, Guide.is_active == True).first()
    
    if not guide:
        await callback.answer("Гайд не найден", show_alert=True)
        db.close()
        return
    
    file_id = guide.file_id
    
    if not file_id:
        await callback.answer("Файл гайда пока не загружен. Скоро появится!", show_alert=True)
        db.close()
        return
    
    try:
        # Отправляем файл
        await callback.message.answer_document(
            document=file_id,
            caption=f"📥 {guide.emoji or '💝'} {guide.name}\n\n🎁 Приятного изучения!"
        )
        
        # Создаем клавиатуру с кнопками
        buttons = []
        
        # Если есть связанный курс, добавляем кнопку перехода
        if guide.related_course_slug:
            buttons.append([InlineKeyboardButton(
                text="📚 Перейти к курсу",
                callback_data=f"course_{guide.related_course_slug}"
            )])
        
        # Кнопки навигации
        buttons.append([
            InlineKeyboardButton(text="◀️ К гайдам", callback_data="guides_list"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Отправляем сообщение с кнопками
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=keyboard
        )
        
        await callback.answer("Гайд отправлен!")
    
    except Exception as e:
        await callback.answer(f"Ошибка при отправке: {str(e)}", show_alert=True)
    
    finally:
        db.close()

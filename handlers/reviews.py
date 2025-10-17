from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto
from sqlalchemy.orm import Session

from database import get_db, User
from data import get_active_reviews
from keyboards import get_reviews_navigation_keyboard

router = Router()

REVIEWS_PER_PAGE = 1  # Показываем по одному отзыву за раз


@router.callback_query(F.data == "reviews")
async def show_reviews_page(callback: CallbackQuery):
    """Показать первую страницу отзывов"""
    await show_reviews_page_number(callback, page=0)


@router.callback_query(F.data.startswith("reviews_page_"))
async def show_reviews_page_handler(callback: CallbackQuery):
    """Обработчик переключения страниц отзывов"""
    # Игнорируем нажатие на индикатор текущей страницы
    if callback.data == "reviews_page_current":
        await callback.answer()
        return
    
    page = int(callback.data.split("_")[-1])
    await show_reviews_page_number(callback, page=page)


async def show_reviews_page_number(callback: CallbackQuery, page: int = 0):
    """Показать страницу отзывов с фотографиями"""
    db: Session = get_db()
    
    try:
        # Обновляем активность пользователя
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
        # Получаем все активные отзывы
        all_reviews = get_active_reviews()
        
        if not all_reviews:
            try:
                await callback.message.edit_text(
                    "Пока здесь нет отзывов, но скоро они появятся!",
                    reply_markup=get_reviews_navigation_keyboard(page=0, total_pages=0),
                    parse_mode="Markdown"
                )
            except Exception:
                await callback.message.answer(
                    "Пока здесь нет отзывов, но скоро они появятся!",
                    reply_markup=get_reviews_navigation_keyboard(page=0, total_pages=0),
                    parse_mode="Markdown"
                )
            await callback.answer()
            return
        
        # Сортируем отзывы по порядку
        reviews_sorted = sorted(all_reviews, key=lambda r: r.get('order', 0))
        
        # Фильтруем только отзывы с фото
        reviews_with_photos = [r for r in reviews_sorted if r.get('photo_id')]
        
        if not reviews_with_photos:
            try:
                await callback.message.edit_text(
                    "Отзывы с фотографиями пока не загружены!",
                    reply_markup=get_reviews_navigation_keyboard(page=0, total_pages=0),
                    parse_mode="Markdown"
                )
            except Exception:
                await callback.message.answer(
                    "Отзывы с фотографиями пока не загружены!",
                    reply_markup=get_reviews_navigation_keyboard(page=0, total_pages=0),
                    parse_mode="Markdown"
                )
            await callback.answer()
            return
        
        # Вычисляем пагинацию
        total_reviews = len(reviews_with_photos)
        total_pages = (total_reviews + REVIEWS_PER_PAGE - 1) // REVIEWS_PER_PAGE
        
        # Проверяем корректность номера страницы
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1
        
        # Получаем отзыв для текущей страницы (по одному)
        current_review = reviews_with_photos[page]
        
        # Пытаемся отредактировать текущее сообщение
        try:
            await callback.message.edit_media(
                media=InputMediaPhoto(
                    media=current_review['photo_id']
                ),
                reply_markup=get_reviews_navigation_keyboard(page=page, total_pages=total_pages)
            )
        except Exception:
            # Если не получилось отредактировать, удаляем старое и отправляем новое
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=current_review['photo_id'],
                reply_markup=get_reviews_navigation_keyboard(page=page, total_pages=total_pages)
            )
        
        await callback.answer()
    
    finally:
        db.close()


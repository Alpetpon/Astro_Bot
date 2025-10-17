"""
Обработчики для управления отзывами в админ-панели (JSON)
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
from datetime import datetime

from data import (
    get_all_reviews,
    get_review_by_id,
    get_all_courses,
    save_review,
    delete_review
)
from utils.bot_settings import is_admin

router = Router()


def transliterate(text: str) -> str:
    """Транслитерация русского текста в латиницу для ID"""
    translit_dict = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    
    text = text.lower()
    result = ''
    for char in text:
        if char in translit_dict:
            result += translit_dict[char]
        elif char.isalnum() or char in '-_':
            result += char
        elif char.isspace():
            result += '-'
    
    # Убираем повторяющиеся дефисы и дефисы в начале/конце
    result = re.sub(r'-+', '-', result)
    result = result.strip('-')
    
    return result


class ReviewManagement(StatesGroup):
    """Состояния для управления отзывами"""
    creating_description = State()
    creating_photo = State()
    editing_description = State()
    editing_photo = State()


# ==================== Список и создание отзывов ====================

@router.callback_query(F.data == "admin_reviews")
async def show_reviews_management(callback: CallbackQuery):
    """Управление отзывами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    reviews = get_all_reviews()
    
    text = f"⭐️ <b>Управление отзывами</b>\n\n"
    text += f"📊 Всего отзывов: {len(reviews)}\n\n"
    
    if reviews:
        for review in sorted(reviews, key=lambda r: r.get('order', 0)):
            status = "✅" if review.get('is_active', True) else "❌"
            photo_status = "📷" if review.get('photo_id') else "⚠️"
            text += f"{status} {photo_status} {review.get('description', review['id'])}\n"
    else:
        text += "Отзывы пока не созданы\n"
    
    text += "\n💡 Нажмите на отзыв для редактирования"
    
    # Создаём клавиатуру
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем кнопки для каждого отзыва
    for review in reviews:
        photo_status = "📷" if review.get('photo_id') else "⚠️"
        keyboard.button(
            text=f"{photo_status} {review.get('description', review['id'])}",
            callback_data=f"manage_review_{review['id']}"
        )
    
    # Кнопка создания нового отзыва
    keyboard.button(text="➕ Создать новый отзыв", callback_data="create_review_start")
    keyboard.button(text="🔙 Назад в админ-панель", callback_data="admin_panel")
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data == "create_review_start")
async def create_review_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания нового отзыва"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.set_state(ReviewManagement.creating_description)
    await callback.message.edit_text(
        "⭐️ <b>Создание нового отзыва</b>\n\n"
        "Шаг 1/2: Введите описание отзыва\n"
        "(краткое название для админки):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_reviews")]
        ])
    )
    await callback.answer()


@router.message(ReviewManagement.creating_description)
async def create_review_description(message: Message, state: FSMContext):
    """Сохранение описания и запрос фотографии"""
    description = message.text
    
    # Генерируем ID
    review_id = f"review_{transliterate(description)}_{int(datetime.now().timestamp())}"
    
    await state.update_data(description=description, review_id=review_id)
    await state.set_state(ReviewManagement.creating_photo)
    
    await message.answer(
        "⭐️ <b>Создание нового отзыва</b>\n\n"
        f"Описание: {description}\n"
        f"ID: <code>{review_id}</code>\n\n"
        "Шаг 2/2: Отправьте фотографию отзыва\n"
        "(или отправьте '-' если хотите добавить позже):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_reviews")]
        ])
    )


@router.message(ReviewManagement.creating_photo)
async def create_review_save(message: Message, state: FSMContext):
    """Сохранение отзыва в JSON"""
    data = await state.get_data()
    
    # Получаем photo_id
    photo_id = None
    if message.photo:
        # Берем фото с наибольшим разрешением
        photo_id = message.photo[-1].file_id
    elif message.text and message.text != '-':
        photo_id = message.text.strip()
    
    try:
        # Определяем максимальный order
        reviews = get_all_reviews()
        max_order = max([r.get('order', 0) for r in reviews], default=0)
        
        # Создаём новый отзыв
        new_review = {
            'id': data['review_id'],
            'description': data['description'],
            'photo_id': photo_id,
            'order': max_order + 1,
            'is_active': True
        }
        
        save_review(new_review)
        
        photo_status = "✅" if photo_id else "⚠️ Без фото"
        text = (
            "✅ <b>Отзыв успешно создан и сохранен в JSON!</b>\n\n"
            f"Описание: {new_review['description']}\n"
            f"ID: {new_review['id']}\n"
            f"Фото: {photo_status}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К списку отзывов", callback_data="admin_reviews")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании отзыва: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К списку отзывов", callback_data="admin_reviews")]
            ])
        )
    finally:
        await state.clear()


# ==================== Управление отзывом ====================

@router.callback_query(F.data.startswith("manage_review_"))
async def manage_review(callback: CallbackQuery):
    """Управление конкретным отзывом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    review_id = callback.data.replace("manage_review_", "")
    review = get_review_by_id(review_id)
    
    if not review:
        await callback.answer("❌ Отзыв не найден", show_alert=True)
        return
    
    status_text = "Активен ✅" if review.get('is_active', True) else "Неактивен ❌"
    photo_text = "Загружено ✅" if review.get('photo_id') else "Не загружено ❌"
    
    text = (
        f"⭐️ <b>{review.get('description', review['id'])}</b>\n\n"
        f"ID: <code>{review['id']}</code>\n"
        f"Описание: {review.get('description', '-')}\n"
        f"Фото: {photo_text}\n"
        f"Статус: {status_text}\n"
        f"Порядок: {review.get('order', 0)}"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Описание", callback_data=f"edit_review_description_{review_id}")
    keyboard.button(text="📷 Фото", callback_data=f"edit_review_photo_{review_id}")
    
    toggle_text = "🔴 Деактивировать" if review.get('is_active', True) else "🟢 Активировать"
    keyboard.button(text=toggle_text, callback_data=f"toggle_review_{review_id}")
    
    keyboard.button(text="🗑 Удалить отзыв", callback_data=f"delete_review_confirm_{review_id}")
    keyboard.button(text="🔙 К списку отзывов", callback_data="admin_reviews")
    keyboard.adjust(2, 1, 1, 1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_review_"))
async def toggle_review(callback: CallbackQuery):
    """Переключение активности отзыва"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    review_id = callback.data.replace("toggle_review_", "")
    review = get_review_by_id(review_id)
    
    if review:
        review['is_active'] = not review.get('is_active', True)
        save_review(review)
        
        await callback.answer(
            f"✅ Отзыв {'активирован' if review['is_active'] else 'деактивирован'}",
            show_alert=True
        )
        # Обновляем сообщение
        await manage_review(callback)
    else:
        await callback.answer("❌ Отзыв не найден", show_alert=True)


@router.callback_query(F.data.startswith("delete_review_confirm_"))
async def delete_review_confirm(callback: CallbackQuery):
    """Подтверждение удаления отзыва"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    review_id = callback.data.replace("delete_review_confirm_", "")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_review_{review_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_review_{review_id}")
        ]
    ])
    
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены, что хотите удалить этот отзыв?</b>\n\n"
        "Это действие нельзя отменить!",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_review_"))
async def delete_review_handler(callback: CallbackQuery):
    """Удаление отзыва"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Извлекаем review_id из callback_data
    # delete_review_confirm_ уже обработан выше, здесь только delete_review_
    parts = callback.data.split("_")
    if len(parts) >= 3 and parts[0] == "delete" and parts[1] == "review":
        # Собираем review_id из оставшихся частей
        review_id = "_".join(parts[2:])
    else:
        await callback.answer("❌ Неверный формат ID", show_alert=True)
        return
    
    review = get_review_by_id(review_id)
    
    if review:
        author_name = review.get('author_name', 'Аноним')
        if delete_review(review_id):
            await callback.answer(f"✅ Отзыв '{author_name}' удален", show_alert=True)
            await show_reviews_management(callback)
        else:
            await callback.answer("❌ Ошибка при удалении", show_alert=True)
    else:
        await callback.answer("❌ Отзыв не найден", show_alert=True)


# ==================== Редактирование отзыва ====================

@router.callback_query(F.data.startswith("edit_review_description_"))
async def edit_review_description_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования описания"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    review_id = callback.data.replace("edit_review_description_", "")
    review = get_review_by_id(review_id)
    
    if not review:
        await callback.answer("❌ Отзыв не найден", show_alert=True)
        return
    
    await state.update_data(editing_review_id=review_id)
    await state.set_state(ReviewManagement.editing_description)
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование описания</b>\n\n"
        f"Текущее описание: {review.get('description', '-')}\n\n"
        f"Введите новое описание:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_review_{review_id}")]
        ])
    )
    await callback.answer()


@router.message(ReviewManagement.editing_description)
async def edit_review_description_save(message: Message, state: FSMContext):
    """Сохранение нового описания"""
    data = await state.get_data()
    review_id = data.get('editing_review_id')
    
    review = get_review_by_id(review_id)
    
    if review:
        review['description'] = message.text
        save_review(review)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К отзыву", callback_data=f"manage_review_{review_id}")]
        ])
        
        await message.answer(
            f"✅ Описание обновлено!\n\nНовое описание: {message.text}",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Отзыв не найден")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_review_photo_"))
async def edit_review_photo_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования фотографии"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    review_id = callback.data.replace("edit_review_photo_", "")
    review = get_review_by_id(review_id)
    
    if not review:
        await callback.answer("❌ Отзыв не найден", show_alert=True)
        return
    
    await state.update_data(editing_review_id=review_id)
    await state.set_state(ReviewManagement.editing_photo)
    
    photo_status = "Загружено ✅" if review.get('photo_id') else "Не загружено ❌"
    
    await callback.message.edit_text(
        f"📷 <b>Редактирование фотографии</b>\n\n"
        f"Текущее фото: {photo_status}\n\n"
        f"Отправьте новую фотографию или file_id\n"
        f"(или отправьте '-' чтобы удалить фото):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_review_{review_id}")]
        ])
    )
    await callback.answer()


@router.message(ReviewManagement.editing_photo)
async def edit_review_photo_save(message: Message, state: FSMContext):
    """Сохранение новой фотографии"""
    data = await state.get_data()
    review_id = data.get('editing_review_id')
    
    review = get_review_by_id(review_id)
    
    if review:
        # Получаем photo_id
        if message.photo:
            # Берем фото с наибольшим разрешением
            review['photo_id'] = message.photo[-1].file_id
        elif message.text and message.text != '-':
            review['photo_id'] = message.text.strip()
        else:
            review['photo_id'] = None
        
        save_review(review)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К отзыву", callback_data=f"manage_review_{review_id}")]
        ])
        
        photo_status = "загружено ✅" if review.get('photo_id') else "удалено ❌"
        await message.answer(
            f"✅ Фото {photo_status}!",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Отзыв не найден")
    
    await state.clear()


from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from database import get_db, UserRepository
from data import get_active_guides, get_guide_by_id, get_mini_course, get_mini_course_tariff
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_guides_list_keyboard, get_guide_keyboard, get_about_me_keyboard, get_mini_course_keyboard, get_mini_course_tariff_keyboard

router = Router()


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    """Показать главное меню"""
    db = await get_db()
    user_repo = UserRepository(db)
    
    # Обновляем активность пользователя
    await user_repo.update_activity(callback.from_user.id)
    
    try:
        await callback.message.edit_text(
            "🏠 **Главное меню**",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать
        # Проверяем, это видео (приветствие) или фото (отзывы)
        if callback.message.video:
            # Если это приветственное видео - НЕ удаляем, просто отправляем новое меню
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text="🏠 **Главное меню**\n\nВыберите интересующий раздел:",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если это фото или другое сообщение - удаляем и отправляем новое
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text="🏠 **Главное меню**\n\nВыберите интересующий раздел:",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
    await callback.answer()


@router.callback_query(F.data == "about_me")
async def show_about_me(callback: CallbackQuery):
    """Показать информацию о преподавателе с кнопками соц. сетей"""
    
    # Отправляем только текст без видео
    text = config.ABOUT_ME_TEXT + "\n\nПереходите в мои соц. сети:"
    await callback.message.edit_text(
        text,
        reply_markup=get_about_me_keyboard(),
        parse_mode="Markdown"
    )
    
    await callback.answer()



@router.callback_query(F.data == "guides_list")
async def show_guides_list(callback: CallbackQuery):
    """Показать список всех гайдов"""
    text = "💕 **Гайды**\n\nВыберите интересующий гайд:"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_guides_list_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать
        # Проверяем, это видео или другое сообщение
        if callback.message.video:
            # Если видео - НЕ удаляем, просто отправляем новое
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_guides_list_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если это фото или другое - удаляем и отправляем новое
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_guides_list_keyboard(),
                parse_mode="Markdown"
            )
    await callback.answer()


@router.callback_query(F.data.startswith("guide_"))
async def show_guide(callback: CallbackQuery):
    """Показать информацию о конкретном гайде"""
    guide_id = callback.data.replace("guide_", "")
    
    # Находим гайд в JSON
    guide = get_guide_by_id(guide_id)
    
    if not guide or not guide.get('is_active', True):
        await callback.answer("Гайд не найден", show_alert=True)
        return
    
    # Гайды бесплатные, проверяем наличие файла
    has_file = bool(guide.get('file_id'))
    related_course_slug = guide.get('related_course_slug')
    
    await callback.message.edit_text(
        guide.get('description') or guide['name'],
        reply_markup=get_guide_keyboard(guide_id, has_file, related_course_slug),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("download_guide_"))
async def download_guide(callback: CallbackQuery):
    """Скачать гайд (бесплатно)"""
    guide_id = callback.data.replace("download_guide_", "")
    
    # Находим гайд в JSON
    guide = get_guide_by_id(guide_id)
    
    if not guide or not guide.get('is_active', True):
        await callback.answer("Гайд не найден", show_alert=True)
        return
    
    file_id = guide.get('file_id')
    
    if not file_id:
        await callback.answer("Файл гайда пока не загружен. Скоро появится!", show_alert=True)
        return
    
    try:
        # Отправляем файл
        await callback.message.answer_document(
            document=file_id,
            caption=f"📥 {guide.get('emoji') or '💝'} {guide['name']}\n\n🎁 Приятного изучения!"
        )
        
        # Создаем клавиатуру с кнопками
        buttons = []
        
        # Если есть связанный курс, добавляем кнопку перехода
        if guide.get('related_course_slug'):
            buttons.append([InlineKeyboardButton(
                text="📚 Перейти к курсу",
                callback_data=f"course_{guide['related_course_slug']}"
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


@router.callback_query(F.data == "mini_course")
async def show_mini_course(callback: CallbackQuery):
    """Показать информацию о мини-курсе (по умолчанию - О курсе)"""
    await show_mini_course_about(callback)


@router.callback_query(F.data == "mini_course_about")
async def show_mini_course_about(callback: CallbackQuery):
    """Показать раздел 'О курсе'"""
    mini_course = get_mini_course()
    
    if not mini_course or not mini_course.get('is_active', False):
        await callback.answer("Мини-курс пока недоступен", show_alert=True)
        return
    
    # Формируем текст "О курсе"
    text = f"{mini_course['emoji']} {mini_course['title']}\n"
    text += f"{mini_course['subtitle']}\n\n"
    text += f"📅 Старт: {mini_course['start_date']}\n\n"
    text += f"{mini_course['description']}\n\n"
    
    # Что получишь
    text += "💎 В итоге ты получишь:\n\n"
    for benefit in mini_course.get('benefits', []):
        text += f"✔️ {benefit}\n"
    text += f"\n{mini_course.get('format', '')}"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_mini_course_keyboard()
        )
    except Exception:
        # Если не можем отредактировать (например, это видео)
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_mini_course_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "mini_course_program")
async def show_mini_course_program(callback: CallbackQuery):
    """Показать раздел 'Программа'"""
    mini_course = get_mini_course()
    
    if not mini_course or not mini_course.get('is_active', False):
        await callback.answer("Мини-курс пока недоступен", show_alert=True)
        return
    
    # Формируем текст "Программа"
    text = f"🌟 Программа мини-курса\n\n"
    
    for day_info in mini_course.get('program', []):
        text += f"{day_info['emoji']} День {day_info['day']}. {day_info['title']}\n"
        text += f"{day_info['description']}\n"
        text += f"✨ {day_info['practice']}\n\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_mini_course_keyboard()
        )
    except Exception:
        pass
    
    await callback.answer()


@router.callback_query(F.data == "mini_course_price")
async def show_mini_course_price(callback: CallbackQuery):
    """Показать раздел 'Стоимость'"""
    mini_course = get_mini_course()
    
    if not mini_course or not mini_course.get('is_active', False):
        await callback.answer("Мини-курс пока недоступен", show_alert=True)
        return
    
    # Формируем текст "Стоимость"
    text = f"💰 Стоимость участия\n\n"
    
    for tariff in mini_course.get('tariffs', []):
        text += f"{tariff['emoji']} {tariff['name']} - {tariff['price']} ₽\n\n"
        text += "Что входит:\n"
        for feature in tariff.get('features', []):
            text += f"✔️ {feature}\n"
        text += "\n"
    
    text += f"{mini_course.get('summary', '')}"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_mini_course_keyboard()
        )
    except Exception:
        pass
    
    await callback.answer()


@router.callback_query(F.data == "mini_course_register")
async def show_mini_course_tariff_selection(callback: CallbackQuery):
    """Показать выбор тарифа для записи на мини-курс"""
    mini_course = get_mini_course()
    
    if not mini_course or not mini_course.get('is_active', False):
        await callback.answer("Мини-курс пока недоступен", show_alert=True)
        return
    
    tariffs = mini_course.get('tariffs', [])
    
    if not tariffs:
        await callback.answer("Тарифы не найдены", show_alert=True)
        return
    
    text = f"📝 Выберите тариф\n\n"
    text += f"Мини-курс: {mini_course.get('title', 'Мини-курс')}\n"
    text += f"{mini_course.get('subtitle', '')}\n\n"
    text += "Выберите подходящий вам вариант обучения:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_mini_course_tariff_keyboard()
    )
    await callback.answer()

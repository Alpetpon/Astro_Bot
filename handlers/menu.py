from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import config
from database import get_db, UserRepository
from data import get_active_guides, get_guide_by_id, get_mini_course, get_mini_course_tariff, get_course_by_slug
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_guides_list_keyboard, get_guide_keyboard, get_about_me_keyboard, get_mini_course_keyboard, get_mini_course_tariff_keyboard

router = Router()


@router.callback_query(F.data == "back_navigation")
async def navigate_back(callback: CallbackQuery, state: FSMContext):
    """Универсальный обработчик кнопки 'Назад' с использованием истории навигации"""
    # Получаем целевой callback из FSM
    data = await state.get_data()
    target_callback = data.get('back_target', 'main_menu')
    
    # Создаем временный mock объект с нужным callback_data
    # Вместо изменения frozen объекта, создаем wrapper
    class CallbackDataWrapper:
        def __init__(self, original_callback, new_data):
            self._original = original_callback
            self.data = new_data
            
        def __getattr__(self, name):
            return getattr(self._original, name)
    
    # Оборачиваем callback с новым data
    wrapped_callback = CallbackDataWrapper(callback, target_callback)
    
    # Определяем какой handler вызвать на основе callback_data
    # Импортируем handlers из других модулей при необходимости
    from . import courses, consultations, reviews, cabinet
    
    # Маппинг callback_data на handlers
    handlers_map = {
        'main_menu': show_main_menu,
        'guides_list': show_guides_list,
        'about_me': show_about_me,
        'mini_course': show_mini_course,
        'mini_course_price': show_mini_course_price,
        'webinar': show_webinar,
        'courses': courses.show_courses_catalog,
        'consultations': consultations.show_consultations_catalog,
        'reviews': reviews.show_reviews_page,
        'my_cabinet': cabinet.show_my_cabinet,
        'my_courses': cabinet.show_my_courses,
    }
    
    # Добавляем обработчики подписок, если они доступны
    try:
        from . import subscription_handlers
        handlers_map['subscription_channel'] = subscription_handlers.show_subscription_channel
        handlers_map['subscription_status'] = subscription_handlers.show_subscription_status
    except ImportError:
        pass
    
    # Если это специфичный callback (например, course_xxx), обрабатываем отдельно
    if target_callback.startswith('course_register_'):
        await courses.show_tariff_selection(wrapped_callback)
    elif target_callback.startswith('course_price_'):
        await courses.show_course_price(wrapped_callback)
    elif target_callback.startswith('course_'):
        await courses.show_course_detail(wrapped_callback)
    elif target_callback.startswith('guide_'):
        await show_guide(wrapped_callback)
    elif target_callback.startswith('consultation_'):
        # consultation_, consultation_info_, consultation_details_, consultation_price_ 
        # все обрабатываются одним handler
        await consultations.show_consultation_detail(wrapped_callback)
    elif target_callback.startswith('mini_course_'):
        # Обрабатываем подразделы мини-курса
        if target_callback == 'mini_course_about':
            await show_mini_course_about(wrapped_callback)
        elif target_callback == 'mini_course_program':
            await show_mini_course_program(wrapped_callback)
        elif target_callback == 'mini_course_price':
            await show_mini_course_price(wrapped_callback)
        elif target_callback == 'mini_course_register':
            await show_mini_course_tariff_selection(wrapped_callback)
        else:
            await show_mini_course(wrapped_callback)
    elif target_callback.startswith('my_course_'):
        await cabinet.show_my_course(wrapped_callback)
    elif target_callback.startswith('reviews_page_'):
        await reviews.show_reviews_page(wrapped_callback)
    elif target_callback in handlers_map:
        # Вызываем соответствующий handler
        handler = handlers_map[target_callback]
        await handler(wrapped_callback)
    else:
        # По умолчанию - главное меню
        await show_main_menu(wrapped_callback)


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    """Показать главное меню"""
    from utils.bot_settings import get_setting, WELCOME_VIDEO_KEY
    
    db = await get_db()
    user_repo = UserRepository(db)
    
    # Обновляем активность пользователя
    await user_repo.update_activity(callback.from_user.id)
    
    # Получаем file_id видео
    welcome_video_id = await get_setting(WELCOME_VIDEO_KEY) or config.WELCOME_VIDEO_FILE_ID
    
    # Если это уже видео с меню - просто редактируем caption
    if callback.message.video and welcome_video_id:
        try:
            await callback.message.edit_caption(
                caption=config.MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return
        except Exception:
            pass
    
    # Для всех остальных случаев - удаляем текущее сообщение и отправляем видео с меню
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Отправляем видео с меню
    if welcome_video_id:
        try:
            await callback.bot.send_video(
                chat_id=callback.message.chat.id,
                video=welcome_video_id,
                caption=config.MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard()
            )
        except Exception:
            # Если не удалось отправить видео, отправляем только текст
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=config.MAIN_MENU_TEXT,
                reply_markup=get_main_menu_keyboard()
            )
    else:
        # Если видео не настроено, отправляем только текст
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=config.MAIN_MENU_TEXT,
            reply_markup=get_main_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "about_me")
async def show_about_me(callback: CallbackQuery):
    """Показать информацию о преподавателе с кнопками соц. сетей"""
    
    text = config.ABOUT_ME_TEXT + "\n\nПодписывайтесь на мои соц. сети:"
    
    try:
        # Пробуем отредактировать сообщение
        if callback.message.video:
            # Если это видео с caption - не можем редактировать на текст, удаляем
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_about_me_keyboard(),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            # Если текст - редактируем текст
            await callback.message.edit_text(
                text,
                reply_markup=get_about_me_keyboard(),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
    except Exception:
        # Если не можем отредактировать - удаляем и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_about_me_keyboard(),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    
    await callback.answer()



@router.callback_query(F.data == "guides_list")
async def show_guides_list(callback: CallbackQuery):
    """Показать список всех гайдов"""
    text = "💕 **Гайды**\n\nВыберите и скачайте гайд"
    
    try:
        # Если это видео - не можем отредактировать, удаляем
        if callback.message.video:
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_guides_list_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если текст - пробуем отредактировать
            await callback.message.edit_text(
                text,
                reply_markup=get_guides_list_keyboard(),
                parse_mode="Markdown"
            )
    except Exception:
        # Если не можем отредактировать - удаляем и отправляем новое
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
        # Создаем клавиатуру с кнопками
        buttons = []
        
        # Если есть связанный курс, добавляем кнопку перехода
        if guide.get('related_course_slug'):
            course = get_course_by_slug(guide['related_course_slug'])
            if course:
                button_text = f"{course.get('emoji', '📚')} Курс «{course['name']}»"
            else:
                button_text = "📚 Перейти к курсу"
            
            buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"course_{guide['related_course_slug']}"
            )])
        
        # Кнопки навигации - используем back_navigation для возврата
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Удаляем предыдущее сообщение с описанием
        try:
            await callback.message.delete()
        except Exception:
            pass  # Игнорируем ошибки удаления
        
        # Отправляем файл с кнопками
        await callback.message.answer_document(
            document=file_id,
            caption=f"{guide.get('emoji') or '💝'} {guide['name']}",
            reply_markup=keyboard
        )
        
        await callback.answer("Гайд отправлен!")
    
    except Exception as e:
        await callback.answer(f"Ошибка при отправке: {str(e)}", show_alert=True)


@router.callback_query(F.data == "mini_course")
async def show_mini_course(callback: CallbackQuery):
    """Показать информацию о мини-курсе - всё в одном сообщении"""
    mini_course = get_mini_course()
    
    if not mini_course or not mini_course.get('is_active', False):
        await callback.answer("Мини-курс пока недоступен", show_alert=True)
        return
    
    # Формируем полный текст с всей информацией
    text = f"{mini_course['emoji']} {mini_course['title']}\n"
    text += f"{mini_course['subtitle']}\n\n"
    text += f"📅 Старт: {mini_course['start_date']}\n\n"
    text += f"{mini_course['description']}\n\n"
    
    # Программа
    text += "📋 **Программа:**\n\n"
    for day_info in mini_course.get('program', []):
        text += f"{day_info['emoji']} День {day_info['day']}. {day_info['title']}\n"
        text += f"{day_info['description']}\n"
        text += f"✨ {day_info['practice']}\n\n"
    
    # Что получишь
    text += "💎 **В итоге ты получишь:**\n\n"
    for benefit in mini_course.get('benefits', []):
        text += f"✔️ {benefit}\n"
    text += f"\n{mini_course.get('format', '')}"
    
    try:
        # Если это видео - удаляем и отправляем новое сообщение
        if callback.message.video:
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_mini_course_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если текст - редактируем
            await callback.message.edit_text(
                text,
                reply_markup=get_mini_course_keyboard(),
                parse_mode="Markdown"
            )
    except Exception:
        # Если не можем отредактировать - удаляем и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_mini_course_keyboard(),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data == "mini_course_about")
async def show_mini_course_about(callback: CallbackQuery):
    """Показать раздел 'О курсе' - перенаправление на основной обработчик"""
    await show_mini_course(callback)


@router.callback_query(F.data == "mini_course_program")
async def show_mini_course_program(callback: CallbackQuery):
    """Показать раздел 'Программа' - перенаправление на основной обработчик"""
    await show_mini_course(callback)


@router.callback_query(F.data == "mini_course_price")
async def show_mini_course_price(callback: CallbackQuery):
    """Показать выбор тарифа для покупки"""
    mini_course = get_mini_course()
    
    if not mini_course or not mini_course.get('is_active', False):
        await callback.answer("Мини-курс пока недоступен", show_alert=True)
        return
    
    tariffs = mini_course.get('tariffs', [])
    
    if not tariffs:
        await callback.answer("Тарифы не найдены", show_alert=True)
        return
    
    # Формируем текст с описанием тарифов
    text = f"💰 **Стоимость участия**\n\n"
    
    # Добавляем информацию о каждом тарифе
    for tariff in tariffs:
        emoji = tariff.get('emoji', '📚')
        name = tariff.get('name', '')
        price = tariff.get('price', 0)
        
        text += f"{emoji} **{name}** — {price} ₽\n\n"
        text += "Что входит:\n"
        for feature in tariff.get('features', []):
            text += f"✔️ {feature}\n"
        text += "\n"
    
    text += f"{mini_course.get('summary', '')}\n\n"
    text += "Выберите подходящий вам вариант обучения:"
    
    # Создаем кнопки с тарифами
    buttons = []
    for tariff in tariffs:
        emoji = tariff.get('emoji', '📚')
        name = tariff.get('name', '')
        price = tariff.get('price', 0)
        tariff_id = tariff.get('id', '')
        
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {name} — {price} ₽",
            callback_data=f"tariff_mini_course_{tariff_id}"
        )])
    
    # Кнопка "Назад" к основной информации
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data == "mini_course_register")
async def show_mini_course_tariff_selection(callback: CallbackQuery):
    """Показать выбор тарифа для записи на мини-курс - перенаправление"""
    await show_mini_course_price(callback)


@router.callback_query(F.data == "webinar")
async def show_webinar(callback: CallbackQuery):
    """Показать информацию о вебинаре"""
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Текст о вебинаре (можно изменить на нужный)
    text = """🎥 **Вебинар**

Здесь будет информация о предстоящих вебинарах.

Следите за обновлениями!"""
    
    try:
        # Если это видео - удаляем и отправляем новое сообщение
        if callback.message.video:
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=get_back_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если текст - редактируем
            await callback.message.edit_text(
                text,
                reply_markup=get_back_keyboard(),
                parse_mode="Markdown"
            )
    except Exception:
        # Если не можем отредактировать - удаляем и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data == "support")
async def show_support(callback: CallbackQuery):
    """Показать информацию о поддержке"""
    # Обновляем активность пользователя
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    text = f"""💬 **Поддержка**

Если у вас возникли вопросы или нужна помощь, вы можете связаться с нами:

📱 **Telegram:** @{config.CONSULTATION_TELEGRAM}

Мы ответим вам в течение 24 часов.

🕐 **Часы работы поддержки:**
Понедельник - Пятница: 10:00 - 19:00 (МСК)
Суббота - Воскресенье: выходной

Также вы можете изучить наши материалы или посмотреть отзывы других учеников, чтобы найти ответы на свои вопросы."""
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать - удаляем и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    
    await callback.answer()

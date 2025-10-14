from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура приветствия"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Перейти в меню", callback_data="main_menu")]
    ])
    return keyboard


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Обо мне", callback_data="about_me")],
        [InlineKeyboardButton(text="💕 Гайды", callback_data="guides_list")],
        [InlineKeyboardButton(text="🔮 Консультации", callback_data="consultations")],
        [InlineKeyboardButton(text="📚 Курсы", callback_data="courses")],
        [InlineKeyboardButton(text="🏠 Мой кабинет", callback_data="my_cabinet")]
    ])
    return keyboard


def get_back_keyboard(callback: str = "main_menu", text: str = "◀️ Назад в меню") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback)]
    ])
    return keyboard


def get_about_me_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела Обо мне с соц. сетями"""
    from config import config
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📷 Instagram", url=config.INSTAGRAM_URL)],
        [InlineKeyboardButton(text="🎥 YouTube", url=config.YOUTUBE_URL)],
        [InlineKeyboardButton(text="💙 ВКонтакте", url=config.VK_URL)],
        [InlineKeyboardButton(text="✈️ Telegram канал", url=config.TELEGRAM_CHANNEL_URL)],
        [InlineKeyboardButton(text="📰 Дзен", url=config.DZEN_URL)],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu")]
    ])
    return keyboard


def get_guides_list_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура списка гайдов (работает с JSON)"""
    from data import get_active_guides
    
    buttons = []
    
    # Получаем активные гайды из JSON
    guides = get_active_guides()
    # Сортируем по порядку
    guides_sorted = sorted(guides, key=lambda g: g.get('order', 0))
    
    for guide in guides_sorted:
        buttons.append([InlineKeyboardButton(
            text=f"{guide.get('emoji') or '💝'} {guide['name']}",
            callback_data=f"guide_{guide['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_guide_keyboard(guide_id: str, has_file: bool = False, related_course_slug: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для конкретного гайда"""
    buttons = []
    
    # Кнопка скачивания (гайды теперь бесплатные)
    if has_file:
        buttons.append([InlineKeyboardButton(text="📥 Скачать PDF", callback_data=f"download_guide_{guide_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="📥 Скачать PDF", callback_data=f"download_guide_{guide_id}")])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ К гайдам", callback_data="guides_list"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_courses_keyboard(courses: List) -> InlineKeyboardMarkup:
    """Клавиатура каталога курсов (работает с JSON dict)"""
    buttons = []
    
    for course in courses:
        # Поддерживаем как объекты БД, так и словари
        name = course.get('name') if isinstance(course, dict) else course.name
        slug = course.get('slug') if isinstance(course, dict) else course.slug
        emoji = course.get('emoji', '📚') if isinstance(course, dict) else getattr(course, 'emoji', '📚')
        
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"course_{slug}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_course_detail_keyboard(course_slug: str, show_navigation: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура карточки курса"""
    buttons = []
    
    # Навигация между разделами
    if show_navigation:
        buttons.append([
            InlineKeyboardButton(text="📖 О курсе", callback_data=f"course_about_{course_slug}"),
            InlineKeyboardButton(text="💰 Стоимость", callback_data=f"course_price_{course_slug}")
        ])
    
    # Кнопка записи
    buttons.append([
        InlineKeyboardButton(text="✅ Записаться", callback_data=f"course_register_{course_slug}")
    ])
    
    # Навигация назад
    buttons.append([
        InlineKeyboardButton(text="◀️ К курсам", callback_data="courses"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_tariff_keyboard(course_slug: str, tariffs: List) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа (работает с JSON dict)"""
    buttons = []
    
    for tariff in tariffs:
        # Поддерживаем как объекты БД, так и словари
        if isinstance(tariff, dict):
            with_support = tariff.get('with_support', False)
            name = tariff.get('name', '')
            price = tariff.get('price', 0)
            tariff_id = tariff.get('id', '')
        else:
            with_support = tariff.with_support
            name = tariff.name
            price = tariff.price
            tariff_id = tariff.id
        
        support_emoji = "👨‍🏫" if with_support else "📚"
        buttons.append([InlineKeyboardButton(
            text=f"{support_emoji} {name} - {price} ₽",
            callback_data=f"tariff_{course_slug}_{tariff_id}"
        )])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад к курсу", callback_data=f"course_{course_slug}")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_payment_keyboard(payment_url: str, payment_id: int) -> InlineKeyboardMarkup:
    """Клавиатура оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="courses")]
    ])
    return keyboard


def get_my_cabinet_keyboard(has_courses: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура личного кабинета"""
    buttons = []
    
    if has_courses:
        buttons.append([InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")])
    
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_my_courses_keyboard(user_courses: List) -> InlineKeyboardMarkup:
    """Клавиатура списка купленных курсов"""
    buttons = []
    
    for course_id, course_name in user_courses:
        buttons.append([InlineKeyboardButton(
            text=f"📖 {course_name}",
            callback_data=f"my_course_{course_id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Мой кабинет", callback_data="my_cabinet")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_course_progress_keyboard(course_id: int, lessons: List) -> InlineKeyboardMarkup:
    """Клавиатура прогресса по курсу"""
    buttons = []
    
    current_module = None
    
    for lesson in lessons:
        if current_module != lesson['module_number']:
            current_module = lesson['module_number']
            buttons.append([InlineKeyboardButton(
                text=f"📂 Модуль {current_module}",
                callback_data=f"module_{course_id}_{current_module}"
            )])
        
        status = "✅" if lesson['is_completed'] else "🔓" if lesson['is_available'] else "🔒"
        buttons.append([InlineKeyboardButton(
            text=f"{status} Урок {lesson['lesson_number']}: {lesson['title'][:30]}...",
            callback_data=f"lesson_{lesson['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Мои курсы", callback_data="my_courses")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_lesson_keyboard(lesson_id: int, course_id: int, has_materials: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура урока"""
    buttons = []
    
    if has_materials:
        buttons.append([InlineKeyboardButton(
            text="📎 Дополнительные материалы",
            callback_data=f"lesson_materials_{lesson_id}"
        )])
    
    buttons.append([
        InlineKeyboardButton(text="✅ Завершить урок", callback_data=f"complete_lesson_{lesson_id}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ К курсу", callback_data=f"my_course_{course_id}")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_consultations_keyboard(consultations: List) -> InlineKeyboardMarkup:
    """Клавиатура каталога консультаций (работает с JSON dict)"""
    buttons = []
    
    for consultation in consultations:
        # Поддерживаем как объекты БД, так и словари
        if isinstance(consultation, dict):
            emoji = consultation.get('emoji', '🔮')
            name = consultation.get('name', '')
            slug = consultation.get('slug', '')
        else:
            emoji = consultation.emoji if consultation.emoji else "🔮"
            name = consultation.name
            slug = consultation.slug
        
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"consultation_{slug}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_consultation_detail_keyboard(consultation_slug: str, show_navigation: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура карточки консультации"""
    buttons = []
    
    # Навигация между разделами
    if show_navigation:
        buttons.append([
            InlineKeyboardButton(text="ℹ️ Инфо", callback_data=f"consultation_info_{consultation_slug}"),
            InlineKeyboardButton(text="📋 Что входит", callback_data=f"consultation_details_{consultation_slug}"),
            InlineKeyboardButton(text="💰 Цены", callback_data=f"consultation_price_{consultation_slug}")
        ])
    
    # Кнопка записи
    buttons.append([
        InlineKeyboardButton(text="✅ Записаться", callback_data=f"consultation_book_{consultation_slug}")
    ])
    
    # Навигация назад
    buttons.append([
        InlineKeyboardButton(text="◀️ К консультациям", callback_data="consultations"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_consultation_options_keyboard(consultation_slug: str, options: List) -> InlineKeyboardMarkup:
    """Клавиатура выбора варианта консультации (работает с JSON dict)"""
    buttons = []
    
    for option in options:
        # Поддерживаем как объекты БД, так и словари
        if isinstance(option, dict):
            name = option.get('name', '')
            duration = option.get('duration')
            price = option.get('price', 0)
            option_id = option.get('id', '')
        else:
            name = option.name
            duration = option.duration
            price = option.price
            option_id = option.id
        
        duration_text = f" ({duration})" if duration else ""
        buttons.append([InlineKeyboardButton(
            text=f"{name}{duration_text} - {price:,.0f} ₽",
            callback_data=f"consultation_option_{consultation_slug}_{option_id}"
        )])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"consultation_{consultation_slug}")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📚 Управление курсами", callback_data="admin_courses")],
        [InlineKeyboardButton(text="🔮 Управление консультациями", callback_data="admin_consultations")],
        [InlineKeyboardButton(text="💕 Управление гайдами", callback_data="admin_guides")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-панель"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_panel")]
    ])
    return keyboard


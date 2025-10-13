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
    """Клавиатура списка гайдов"""
    from config import config
    
    buttons = []
    
    for guide in config.GUIDES:
        buttons.append([InlineKeyboardButton(
            text=f"{guide['emoji']} {guide['name']}",
            callback_data=f"guide_{guide['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад в меню", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_guide_keyboard(guide_id: str, has_file: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для конкретного гайда"""
    buttons = []
    
    if has_file:
        buttons.append([InlineKeyboardButton(text="📥 Скачать гайд", callback_data=f"download_guide_{guide_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="💳 Купить гайд", callback_data=f"buy_guide_{guide_id}")])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ К гайдам", callback_data="guides_list"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_courses_keyboard(courses: List) -> InlineKeyboardMarkup:
    """Клавиатура каталога курсов"""
    buttons = []
    
    for course in courses:
        buttons.append([InlineKeyboardButton(
            text=course.name,
            callback_data=f"course_{course.slug}"
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
    """Клавиатура выбора тарифа"""
    buttons = []
    
    for tariff in tariffs:
        support_emoji = "👨‍🏫" if tariff.with_support else "📚"
        buttons.append([InlineKeyboardButton(
            text=f"{support_emoji} {tariff.name} - {tariff.price} ₽",
            callback_data=f"tariff_{tariff.id}"
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
    """Клавиатура каталога консультаций"""
    buttons = []
    
    for consultation in consultations:
        emoji = consultation.emoji if consultation.emoji else "🔮"
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {consultation.name}",
            callback_data=f"consultation_{consultation.slug}"
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
    """Клавиатура выбора варианта консультации"""
    buttons = []
    
    for option in options:
        duration_text = f" ({option.duration})" if option.duration else ""
        buttons.append([InlineKeyboardButton(
            text=f"{option.name}{duration_text} - {option.price:,.0f} ₽",
            callback_data=f"consultation_option_{option.id}"
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
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📦 Покупки", callback_data="admin_purchases")],
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


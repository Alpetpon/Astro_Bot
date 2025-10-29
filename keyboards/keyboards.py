from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional
from urllib.parse import quote


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура приветствия"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой путь", callback_data="about_me")],
        [InlineKeyboardButton(text="✨ Перейти в меню", callback_data="main_menu")]
    ])
    return keyboard


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой путь", callback_data="about_me")],
        [InlineKeyboardButton(text="💕 Гайды", callback_data="guides_list")],
        [InlineKeyboardButton(text="🌌 Мини-курс", callback_data="mini_course")],
        [InlineKeyboardButton(text="📚 Курсы", callback_data="courses")],
        [InlineKeyboardButton(text="🎥 Вебинар", callback_data="webinar")],
        [InlineKeyboardButton(text="💫 Вступить в закрытый клуб", callback_data="subscription_channel")],
        [InlineKeyboardButton(text="🔮 Консультации", callback_data="consultations")],
        [InlineKeyboardButton(text="🏠 Мой кабинет", callback_data="my_cabinet")],
        [InlineKeyboardButton(text="⭐️ Отзывы", callback_data="reviews")]
    ])
    return keyboard


def get_back_keyboard(callback: str = "main_menu", text: str = "◀️ Назад в меню") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback)]
    ])
    return keyboard


def get_about_me_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела Мой путь с соц. сетями"""
    from config import config
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram канал", url=config.TELEGRAM_CHANNEL_URL)],
        [InlineKeyboardButton(text="YouTube", url=config.YOUTUBE_URL)],
        [InlineKeyboardButton(text="Instagram", url=config.INSTAGRAM_URL)],
        [InlineKeyboardButton(text="Читать на Sponsr", url=config.VK_URL)],
        [InlineKeyboardButton(text="Дзен", url=config.DZEN_URL)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")]
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
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
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
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation"),
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
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_course_detail_keyboard(course_slug: str, show_navigation: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура карточки курса"""
    buttons = []
    
    # Кнопки: Стоимость и Записаться
    buttons.append([
        InlineKeyboardButton(text="💰 Стоимость", callback_data=f"course_price_{course_slug}")
    ])
    buttons.append([
        InlineKeyboardButton(text="✅ Записаться", callback_data=f"course_register_{course_slug}")
    ])
    
    # Навигация назад
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation"),
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
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_payment_keyboard(payment_url: str, payment_id: int, back_callback: str = "back_navigation") -> InlineKeyboardMarkup:
    """Клавиатура оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)]
    ])
    return keyboard


def get_my_cabinet_keyboard(has_courses: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура личного кабинета"""
    buttons = []
    
    if has_courses:
        buttons.append([InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
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
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
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
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
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
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")
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
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_consultation_detail_keyboard(consultation_slug: str, consultation_name: str = "", show_navigation: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура карточки консультации"""
    from config import config
    
    buttons = []
    
    # Заготовленное сообщение для записи на консультацию
    if consultation_name:
        message_text = f"Здравствуйте! Хочу записаться на консультацию: {consultation_name}"
    else:
        message_text = "Здравствуйте! Хочу записаться на консультацию."
    encoded_text = quote(message_text)
    
    # Кнопка записи - ведет в Telegram к астрологу с заготовленным сообщением
    buttons.append([
        InlineKeyboardButton(
            text="✅ Записаться на консультацию", 
            url=f"https://t.me/{config.CONSULTATION_TELEGRAM}?text={encoded_text}"
        )
    ])
    
    # Навигация назад
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation"),
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
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="💳 Создать ссылку на оплату", callback_data="admin_create_payment_link")],
        [InlineKeyboardButton(text="🤖 Управление ботом", callback_data="admin_bot_management")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def get_bot_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подменю управления ботом"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌌 Управление мини-курсом", callback_data="admin_mini_course")],
        [InlineKeyboardButton(text="📚 Управление курсами", callback_data="admin_courses")],
        [InlineKeyboardButton(text="🔮 Управление консультациями", callback_data="admin_consultations")],
        [InlineKeyboardButton(text="💕 Управление гайдами", callback_data="admin_guides")],
        [InlineKeyboardButton(text="⭐️ Управление отзывами", callback_data="admin_reviews")],
        [InlineKeyboardButton(text="💫 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton(text="🎥 Настройки видео", callback_data="admin_video_settings")],
        [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_panel")]
    ])
    return keyboard


def get_admin_subscriptions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления подписками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика подписок", callback_data="admin_subscriptions_stats")],
        [InlineKeyboardButton(text="🗑 Очистить подписки", callback_data="admin_subscriptions_clear")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bot_management")]
    ])
    return keyboard


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-панель"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_panel")]
    ])
    return keyboard


def get_back_to_free_course_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата к управлению бесплатным курсом"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к бесплатному курсу", callback_data="manage_free_course")]
    ])
    return keyboard


def get_video_settings_keyboard(has_welcome_video: bool = False, has_step3_photos: bool = False, has_step3_video: bool = False, has_final_message: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура настроек видео"""
    buttons = []
    
    # Приветственное видео
    if has_welcome_video:
        buttons.append([
            InlineKeyboardButton(text="🔄 Заменить приветственное видео", callback_data="video_welcome_upload")
        ])
        buttons.append([
            InlineKeyboardButton(text="🗑 Удалить приветственное видео", callback_data="video_welcome_delete")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="➕ Загрузить приветственное видео", callback_data="video_welcome_upload")
        ])
    
    # Фото для шага 3 (Инструкция Sotis)
    if has_step3_photos:
        buttons.append([
            InlineKeyboardButton(text="🔄 Заменить фото Шага 3", callback_data="video_step3_photos_upload")
        ])
        buttons.append([
            InlineKeyboardButton(text="🗑 Удалить фото Шага 3", callback_data="video_step3_photos_delete")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="➕ Загрузить фото Шага 3", callback_data="video_step3_photos_upload")
        ])
    
    # Видео для шага 3
    if has_step3_video:
        buttons.append([
            InlineKeyboardButton(text="🔄 Заменить видео Шага 3", callback_data="video_step3_video_upload")
        ])
        buttons.append([
            InlineKeyboardButton(text="🗑 Удалить видео Шага 3", callback_data="video_step3_video_delete")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="➕ Загрузить видео Шага 3", callback_data="video_step3_video_upload")
        ])
    
    # Финальное сообщение
    if has_final_message:
        buttons.append([
            InlineKeyboardButton(text="✏️ Изменить финальное сообщение", callback_data="free_course_final_message_edit")
        ])
        buttons.append([
            InlineKeyboardButton(text="🗑 Удалить финальное сообщение", callback_data="free_course_final_message_delete")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="✏️ Настроить финальное сообщение", callback_data="free_course_final_message_edit")
        ])
    
    # Кнопка назад
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_panel")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_reviews_navigation_keyboard(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Клавиатура навигации по отзывам с фото"""
    buttons = []
    
    # Если страниц больше одной, добавляем навигацию
    if total_pages > 1:
        nav_buttons = []
        
        # Кнопка "Назад"
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"reviews_page_{page - 1}"
            ))
        
        # Кнопка "Далее"
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Далее ▶️",
                callback_data=f"reviews_page_{page + 1}"
            ))
        
        # Добавляем только если есть хотя бы одна кнопка
        if nav_buttons:
            buttons.append(nav_buttons)
    
    # Кнопка перехода к курсам
    buttons.append([InlineKeyboardButton(text="📚 Курсы", callback_data="courses")])
    
    # Кнопка "Главное меню"
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_mini_course_keyboard(show_navigation: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для мини-курса"""
    buttons = []
    
    # Кнопки: Стоимость и Записаться
    buttons.append([
        InlineKeyboardButton(text="💰 Стоимость", callback_data="mini_course_price")
    ])
    buttons.append([
        InlineKeyboardButton(text="✅ Записаться на мини-курс", callback_data="mini_course_register")
    ])
    
    # Назад
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_mini_course_tariff_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа мини-курса"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Самостоятельное изучение — 5000 ₽", callback_data="tariff_mini_course_mini-solo")],
        [InlineKeyboardButton(text="👨‍🏫 С сопровождением — 10000 ₽", callback_data="tariff_mini_course_mini-support")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")]
    ])
    return keyboard


def get_subscription_channel_keyboard(has_active_subscription: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для канала с подпиской"""
    buttons = []
    
    if has_active_subscription:
        buttons.append([InlineKeyboardButton(text="📊 Статус подписки", callback_data="subscription_status")])
    else:
        buttons.append([InlineKeyboardButton(text="💳 Купить доступ", callback_data="subscription_buy")])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_subscription_payment_keyboard(payment_url: str, payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура оплаты подписки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"subscription_check_payment_{payment_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="subscription_channel")]
    ])
    return keyboard


def get_subscription_status_keyboard(can_renew: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура статуса подписки"""
    buttons = []
    
    if can_renew:
        buttons.append([InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="subscription_buy")])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


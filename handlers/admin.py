from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bson import ObjectId
import os
import logging
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

logger = logging.getLogger(__name__)

from config import config
from database import get_db, User, Payment, UserRepository, PaymentRepository
from keyboards import get_admin_keyboard, get_bot_management_keyboard, get_back_to_admin_keyboard
from data import get_all_courses, get_all_consultations
from utils.bot_settings import is_admin

# Заглушки для старых моделей БД (код не используется, проект работает на JSON)
Course = None  # type: ignore
Consultation = None  # type: ignore
Lesson = None  # type: ignore

router = Router()


class CourseManagement(StatesGroup):
    """Состояния для управления курсами"""
    waiting_for_lesson_title = State()
    waiting_for_lesson_description = State()
    waiting_for_lesson_content = State()
    waiting_for_lesson_video = State()
    waiting_for_lesson_lecture_file = State()
    waiting_for_lesson_text_content = State()
    editing_lesson_title = State()
    editing_lesson_description = State()
    editing_lesson_content = State()
    editing_lesson_video = State()


class ConsultationManagement(StatesGroup):
    """Состояния для управления консультациями"""
    editing_name = State()
    editing_price = State()
    editing_duration = State()
    editing_description = State()
    # Создание новой консультации
    creating_name = State()
    creating_slug = State()
    creating_emoji = State()
    creating_price = State()
    creating_duration = State()
    creating_description = State()


class CourseCreation(StatesGroup):
    """Состояния для создания нового курса"""
    waiting_for_name = State()
    waiting_for_slug = State()
    waiting_for_description = State()
    waiting_for_duration = State()


class PaymentLinkCreation(StatesGroup):
    """Состояния для создания платежной ссылки"""
    waiting_for_user_id = State()
    waiting_for_product_type = State()
    waiting_for_product_selection = State()
    waiting_for_amount = State()


class BroadcastStates(StatesGroup):
    """Состояния для рассылки"""
    waiting_for_text = State()
    waiting_for_photo = State()
    waiting_for_video = State()
    waiting_for_caption = State()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Вход в админ-панель по команде /admin"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Показать админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_bot_management")
async def show_bot_management(callback: CallbackQuery):
    """Показать подменю управления ботом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🤖 <b>Управление ботом</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_bot_management_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    # Общая статистика
    total_users = await user_repo.count()
    total_purchases = await payment_repo.count_by_status("succeeded")
    total_revenue = await payment_repo.sum_by_status("succeeded")
    
    # Активные пользователи (за последние 7 дней)
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_users = await user_repo.count_active_since(week_ago)
    
    # Новые пользователи за неделю
    new_users = await user_repo.count_created_since(week_ago)
    
    # Покупки за неделю
    week_purchases = await payment_repo.count_since(week_ago, "succeeded")
    week_revenue = await payment_repo.sum_since(week_ago, "succeeded")
    
    # Курсы, консультации и гайды (из JSON)
    total_courses = len(get_all_courses())
    total_consultations = len(get_all_consultations())
    
    from data import get_all_guides
    total_guides = len(get_all_guides())
    
    # Статистика подписок (если сервис доступен)
    subscription_stats = None
    try:
        from handlers.subscription_handlers import subscription_service
        if subscription_service:
            subscription_stats = await subscription_service.get_subscription_stats()
    except Exception as e:
        logger.warning(f"Could not get subscription stats: {e}")
    
    stats_text = f"""📊 <b>Статистика</b>

👥 <b>Пользователи:</b>
• Всего: {total_users}
• Активных за неделю: {active_users}
• Новых за неделю: {new_users}

💰 <b>Финансы:</b>
• Всего покупок: {total_purchases}
• Общая выручка: {total_revenue:,.0f} ₽
• За неделю покупок: {week_purchases}
• За неделю выручка: {week_revenue:,.0f} ₽

📚 <b>Контент:</b>
• Курсов: {total_courses}
• Консультаций: {total_consultations}
• Гайдов: {total_guides}"""
    
    # Добавляем статистику подписок, если доступна
    if subscription_stats:
        stats_text += f"""

💫 <b>Подписки на канал:</b>
• Всего подписок: {subscription_stats['total_subscriptions']}
• Активных подписок: {subscription_stats['active_subscriptions']}
• Всего платежей: {subscription_stats['total_payments']}
• Успешных платежей: {subscription_stats['succeeded_payments']}
• Общая сумма: {subscription_stats['total_amount']:,.0f} ₽
"""
    
    # Кнопки с возможностью скачать Excel
    buttons = [
        [InlineKeyboardButton(text="📥 Скачать детальную аналитику (Excel)", callback_data="download_analytics")],
        [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_panel")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=keyboard
    )
    
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение для рассылки:\n"
        "• Текст\n"
        "• Фото (с подписью или без)\n"
        "• Видео (с подписью или без)\n\n"
        "Отправьте /cancel для отмены."
    )
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.answer()


@router.message(Command("broadcast"))
async def broadcast_message(message: Message):
    """Рассылка сообщения всем пользователям"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    # Получаем текст сообщения
    text = message.text.replace("/broadcast", "").strip()
    
    if not text:
        await message.answer(
            "❌ Укажите текст сообщения:\n"
            "<code>/broadcast [текст]</code>"
        )
        return
    
    db = await get_db()
    user_repo = UserRepository(db)
    
    # Получаем всех пользователей
    users = await user_repo.get_all()
    
    success_count = 0
    fail_count = 0
    
    status_msg = await message.answer(f"📤 Начинаю рассылку для {len(users)} пользователей...")
    
    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user.telegram_id,
                text=text
            )
            success_count += 1
        except Exception:
            fail_count += 1
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"Успешно: {success_count}\n"
        f"Ошибок: {fail_count}"
    )


# ===== Универсальный обработчик рассылки =====

@router.message(BroadcastStates.waiting_for_text)
async def process_broadcast_content(message: Message, state: FSMContext):
    """Универсальный обработчик для любого контента рассылки"""
    if not is_admin(message.from_user.id):
        return
    
    # Проверка на отмену
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена", reply_markup=get_admin_keyboard())
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить рассылку", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_broadcast")]
    ])
    
    # Обработка фото
    if message.photo:
        photo_id = message.photo[-1].file_id
        caption = message.caption or ""
        
        await state.update_data(photo_id=photo_id, caption=caption, media_type="photo")
        
        preview_text = f"🖼 <b>Превью рассылки</b>\n\n"
        if caption:
            preview_text += f"{caption}\n\n"
        preview_text += "Подтвердите отправку:"
        
        await message.answer_photo(
            photo=photo_id,
            caption=preview_text,
            reply_markup=keyboard
        )
    
    # Обработка видео
    elif message.video:
        video_id = message.video.file_id
        caption = message.caption or ""
        
        await state.update_data(video_id=video_id, caption=caption, media_type="video")
        
        preview_text = f"🎥 <b>Превью рассылки</b>\n\n"
        if caption:
            preview_text += f"{caption}\n\n"
        preview_text += "Подтвердите отправку:"
        
        await message.answer_video(
            video=video_id,
            caption=preview_text,
            reply_markup=keyboard
        )
    
    # Обработка текста
    elif message.text:
        text = message.text
        
        await state.update_data(text=text, media_type="text")
        
        await message.answer(
            f"📝 <b>Превью рассылки:</b>\n\n{text}\n\n"
            "Подтвердите отправку:",
            reply_markup=keyboard
        )
    
    else:
        await message.answer("❌ Поддерживаются только текст, фото или видео")


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_and_send_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и отправка рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    data = await state.get_data()
    media_type = data.get("media_type")
    
    db = await get_db()
    user_repo = UserRepository(db)
    
    users = await user_repo.get_all()
    
    success_count = 0
    fail_count = 0
    
    # Удаляем превью и отправляем новое сообщение о начале рассылки
    try:
        await callback.message.delete()
    except:
        pass
    
    status_msg = await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=f"📤 Начинаю рассылку для {len(users)} пользователей..."
    )
    
    for user in users:
        try:
            if media_type == "text":
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=data["text"]
                )
            elif media_type == "photo":
                await callback.bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=data["photo_id"],
                    caption=data.get("caption")
                )
            elif media_type == "video":
                await callback.bot.send_video(
                    chat_id=user.telegram_id,
                    video=data["video_id"],
                    caption=data.get("caption")
                )
            
            success_count += 1
        except Exception:
            fail_count += 1
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"Успешно: {success_count}\n"
        f"Ошибок: {fail_count}"
    )
    
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin_courses")
async def show_courses_management(callback: CallbackQuery):
    """Показать управление курсами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем курсы из JSON
    courses = get_all_courses()
    
    if not courses:
        await callback.message.edit_text(
            "📚 <b>Курсы отсутствуют</b>\n\n"
            "Курсы хранятся в файле data/courses.json",
            reply_markup=get_back_to_admin_keyboard()
        )
    else:
        buttons = []
        for course in courses:
            buttons.append([InlineKeyboardButton(
                text=f"{course.get('emoji', '📚')} {course['name']}",
                callback_data=f"manage_course_{course['slug']}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="◀️ Назад в админ-панель",
            callback_data="admin_panel"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            "📚 <b>Управление курсами</b>\n\n"
            "Просмотр курсов. Для редактирования используйте файлы data/courses.json и data/course_materials.json",
            reply_markup=keyboard
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("manage_course_"))
async def manage_course(callback: CallbackQuery):
    """Управление конкретным курсом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Извлекаем slug курса
    course_slug = "_".join(callback.data.split("_")[2:])
    
    from data import get_course_by_slug, get_course_materials
    
    course = get_course_by_slug(course_slug)
    
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    
    # Получаем материалы курса
    materials = get_course_materials(course_slug)
    modules = materials.get('modules', []) if materials else []
    
    text = f"📖 <b>{course['name']}</b>\n\n"
    text += f"📍 Slug: <code>{course['slug']}</code>\n"
    
    if course.get('price'):
        text += f"💰 Цена: {course['price']:,.0f} ₽\n"
    
    if course.get('duration'):
        text += f"⏱ Длительность: {course['duration']}\n"
    
    text += f"✅ Активен: {'Да' if course.get('is_active', True) else 'Нет'}\n"
    
    if modules:
        text += f"\n📂 <b>Модулей:</b> {len(modules)}\n\n"
        for module in modules:
            text += f"• {module.get('title', 'Без названия')}\n"
    else:
        text += "\nМодулей пока нет\n"
    
    buttons = []
    
    # Кнопки для просмотра модулей
    if modules:
        buttons.append([InlineKeyboardButton(
            text="📂 Просмотр модулей",
            callback_data=f"view_modules_{course_slug}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="◀️ Назад к курсам",
        callback_data="admin_courses"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("view_modules_"))
async def view_modules(callback: CallbackQuery):
    """Просмотр списка модулей курса"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    course_slug = "_".join(callback.data.split("_")[2:])
    
    from data import get_course_by_slug, get_course_modules
    
    course = get_course_by_slug(course_slug)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    
    modules = get_course_modules(course_slug)
    
    text = f"📂 <b>Модули курса: {course['name']}</b>\n\n"
    
    buttons = []
    for module in modules:
        buttons.append([InlineKeyboardButton(
            text=f"📂 {module.get('title', 'Без названия')}",
            callback_data=f"view_module_{course_slug}_{module['id']}"
        )])
    
    # Кнопка добавления модуля
    buttons.append([InlineKeyboardButton(
        text="➕ Добавить модуль",
        callback_data=f"add_module_{course_slug}"
    )])
    
    buttons.append([InlineKeyboardButton(
        text="◀️ Назад к курсу",
        callback_data=f"manage_course_{course_slug}"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("view_module_"))
async def view_module(callback: CallbackQuery):
    """Просмотр конкретного модуля"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    module_id = parts[-1]
    course_slug = "_".join(parts[2:-1])
    
    from data import get_course_by_slug, get_module_by_id
    
    course = get_course_by_slug(course_slug)
    module = get_module_by_id(course_slug, module_id)
    
    if not course or not module:
        await callback.answer("Модуль не найден", show_alert=True)
        return
    
    text = f"📂 <b>{module['title']}</b>\n\n"
    if module.get('description'):
        text += f"{module['description']}\n\n"
    
    lessons = module.get('lessons', [])
    if lessons:
        text += f"📝 <b>Уроков: {len(lessons)}</b>\n\n"
        for i, lesson in enumerate(lessons, 1):
            text += f"{i}. {lesson.get('title', 'Без названия')}\n"
    else:
        text += "Уроков пока нет\n"
    
    buttons = []
    
    # Кнопки для редактирования уроков
    if lessons:
        for lesson in lessons:
            buttons.append([InlineKeyboardButton(
                text=f"✏️ {lesson.get('title', 'Без названия')[:30]}...",
                callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson['id']}"
            )])
    
    # Кнопка добавления урока
    buttons.append([InlineKeyboardButton(
        text="➕ Добавить урок",
        callback_data=f"add_lesson_to_module_{course_slug}_{module_id}"
    )])
    
    buttons.append([InlineKeyboardButton(
        text="◀️ К модулям",
        callback_data=f"view_modules_{course_slug}"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("add_module_"))
async def add_module_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления модуля"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    course_slug = "_".join(callback.data.split("_")[2:])
    
    await state.update_data(course_slug=course_slug, adding_module=True)
    await state.set_state(CourseManagement.waiting_for_lesson_title)
    
    await callback.message.edit_text(
        "➕ <b>Добавление модуля</b>\n\n"
        "Введите название модуля:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_course_{course_slug}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_lesson_to_module_"))
async def add_lesson_to_module_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления урока в модуль"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    module_id = parts[-1]
    course_slug = "_".join(parts[4:-1])
    
    await state.update_data(
        course_slug=course_slug,
        module_id=module_id,
        adding_lesson=True
    )
    await state.set_state(CourseManagement.waiting_for_lesson_title)
    
    await callback.message.edit_text(
        "➕ <b>Добавление урока</b>\n\n"
        "Введите название урока:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_module_{course_slug}_{module_id}")]
        ])
    )
    await callback.answer()


# Старый обработчик, оставим для совместимости, но перенаправим
@router.callback_query(F.data.startswith("add_lesson_"))
async def add_lesson_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления урока - DEPRECATED"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Перенаправляем на управление курсами
    await callback.answer("⚠️ Используйте новый интерфейс", show_alert=True)
    await callback.message.edit_text(
        "ℹ️ Управление курсами перенесено на новый интерфейс\n\n"
        "Используйте кнопку 'Управление курсами' в админ-панели",
        reply_markup=get_back_to_admin_keyboard()
    )


@router.message(CourseManagement.waiting_for_lesson_title)
async def process_title_input(message: Message, state: FSMContext):
    """Обработка ввода названия (модуля или урока)"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    title = message.text.strip()
    
    # Проверяем что добавляем
    if data.get('adding_module'):
        # Добавляем модуль
        await state.update_data(module_title=title)
        course_slug = data['course_slug']
        
        await message.answer(
            f"✅ Название модуля: <b>{title}</b>\n\n"
            f"Теперь отправьте описание модуля (или отправьте 'пропустить'):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_module_desc_{course_slug}")]
            ])
        )
        await state.set_state(CourseManagement.waiting_for_lesson_description)
        
    elif data.get('adding_lesson'):
        # Добавляем урок
        await state.update_data(lesson_title=title)
        course_slug = data['course_slug']
        module_id = data['module_id']
        
        await message.answer(
            f"✅ Название урока: <b>{title}</b>\n\n"
            f"Теперь отправьте описание урока:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_module_{course_slug}_{module_id}")]
            ])
        )
        await state.set_state(CourseManagement.waiting_for_lesson_description)


@router.callback_query(F.data.startswith("skip_module_desc_"))
async def skip_module_description(callback: CallbackQuery, state: FSMContext):
    """Пропустить описание модуля"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.update_data(module_description="")
    await save_new_module(callback.message, state)
    await callback.answer()


@router.message(CourseManagement.waiting_for_lesson_description)
async def process_description_input(message: Message, state: FSMContext):
    """Обработка ввода описания (модуля или урока)"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    description = message.text.strip()
    
    # Проверяем что добавляем
    if data.get('adding_module'):
        # Сохраняем описание и создаем модуль
        await state.update_data(module_description=description)
        await save_new_module(message, state)
        
    elif data.get('adding_lesson'):
        # Сохраняем описание и просим видео
        await state.update_data(lesson_description=description)
        course_slug = data['course_slug']
        module_id = data['module_id']
        
        await message.answer(
            "✅ Описание сохранено\n\n"
            "Отправьте ссылку на видео (YouTube URL) или нажмите 'Пропустить':",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_lesson_video_{course_slug}_{module_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_module_{course_slug}_{module_id}")]
            ])
        )
        await state.set_state(CourseManagement.waiting_for_lesson_video)


async def save_new_module(message: Message, state: FSMContext):
    """Сохранение нового модуля"""
    data = await state.get_data()
    course_slug = data['course_slug']
    
    from data import add_module_to_course, get_course_modules
    import uuid
    
    # Генерируем ID
    modules = get_course_modules(course_slug)
    module_order = len(modules) + 1
    
    new_module = {
        'id': f"module-{module_order}",
        'title': data.get('module_title', 'Новый модуль'),
        'description': data.get('module_description', ''),
        'order': module_order,
        'lessons': []
    }
    
    try:
        add_module_to_course(course_slug, new_module)
        
        await message.answer(
            f"✅ <b>Модуль успешно добавлен!</b>\n\n"
            f"📂 {new_module['title']}\n\n"
            f"Теперь вы можете добавить уроки в этот модуль.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить урок", callback_data=f"add_lesson_to_module_{course_slug}_{new_module['id']}")],
                [InlineKeyboardButton(text="◀️ К курсу", callback_data=f"manage_course_{course_slug}")]
            ])
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении модуля: {str(e)}")
    
    await state.clear()


@router.callback_query(F.data.startswith("skip_lesson_video_"))
async def skip_lesson_video(callback: CallbackQuery, state: FSMContext):
    """Пропустить видео и перейти к лекции"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.update_data(video_url="")
    
    # Переходим к запросу PDF лекции
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    
    await callback.message.edit_text(
        "Теперь отправьте PDF файл лекции или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_lesson_lecture_{course_slug}_{module_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_module_{course_slug}_{module_id}")]
        ])
    )
    await state.set_state(CourseManagement.waiting_for_lesson_lecture_file)
    await callback.answer()


@router.callback_query(F.data.startswith("skip_lesson_lecture_"))
async def skip_lesson_lecture(callback: CallbackQuery, state: FSMContext):
    """Пропустить PDF лекцию и перейти к текстовому содержимому"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.update_data(lecture_file_id="")
    
    # Переходим к запросу текстового содержимого
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    
    await callback.message.edit_text(
        "Теперь отправьте текстовое содержание урока или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_lesson_text_{course_slug}_{module_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_module_{course_slug}_{module_id}")]
        ])
    )
    await state.set_state(CourseManagement.waiting_for_lesson_text_content)
    await callback.answer()


@router.callback_query(F.data.startswith("skip_lesson_text_"))
async def skip_lesson_text(callback: CallbackQuery, state: FSMContext):
    """Пропустить текстовое содержание и сохранить урок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.update_data(text_content="")
    await save_new_lesson_to_module(callback.message, state)
    await callback.answer()


async def process_lesson_lecture(message: Message, state: FSMContext):
    """Получение PDF лекции для урока (вспомогательная функция для создания нового урока)"""
    if not is_admin(message.from_user.id):
        return
    
    # Проверяем что это PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        await message.answer("❌ Пожалуйста, отправьте PDF файл")
        return
    
    lecture_file_id = message.document.file_id
    await state.update_data(lecture_file_id=lecture_file_id)
    
    # Переходим к запросу текстового содержимого
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    
    await message.answer(
        "✅ PDF лекция сохранена\n\n"
        "Теперь отправьте текстовое содержание урока или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_lesson_text_{course_slug}_{module_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_module_{course_slug}_{module_id}")]
        ])
    )
    await state.set_state(CourseManagement.waiting_for_lesson_text_content)


# Этот обработчик больше не нужен - логика перенесена в save_json_lesson_lecture
# async def invalid_lecture_file(message: Message):
#     """Обработка неверного формата файла лекции"""
#     if not is_admin(message.from_user.id):
#         return
#     
#     await message.answer(
#         "❌ Пожалуйста, отправьте PDF файл (не ссылку, не изображение)\n\n"
#         "Или нажмите 'Пропустить' для продолжения"
#     )


@router.message(CourseManagement.waiting_for_lesson_video)
async def process_lesson_video(message: Message, state: FSMContext):
    """Получение ссылки на видео для урока"""
    if not is_admin(message.from_user.id):
        return
    
    video_url = message.text.strip()
    await state.update_data(video_url=video_url)
    
    # Переходим к запросу PDF лекции
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    
    await message.answer(
        "✅ Ссылка на видео сохранена\n\n"
        "Теперь отправьте PDF файл лекции или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_lesson_lecture_{course_slug}_{module_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_module_{course_slug}_{module_id}")]
        ])
    )
    await state.set_state(CourseManagement.waiting_for_lesson_lecture_file)


@router.message(CourseManagement.waiting_for_lesson_text_content)
async def process_lesson_text_content(message: Message, state: FSMContext):
    """Получение текстового содержания урока"""
    if not is_admin(message.from_user.id):
        return
    
    text_content = message.text.strip()
    await state.update_data(text_content=text_content)
    await save_new_lesson_to_module(message, state)


async def save_new_lesson_to_module(message: Message, state: FSMContext):
    """Сохранение нового урока в модуль"""
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    
    from data import add_lesson_to_module, get_module_by_id
    
    # Получаем модуль чтобы определить порядок урока
    module = get_module_by_id(course_slug, module_id)
    if not module:
        await message.answer("❌ Модуль не найден")
        await state.clear()
        return
    
    lessons_count = len(module.get('lessons', []))
    lesson_order = lessons_count + 1
    
    new_lesson = {
        'id': f"lesson-{module_id}-{lesson_order}",
        'title': data.get('lesson_title', 'Новый урок'),
        'description': data.get('lesson_description', ''),
        'duration': '',
        'type': 'video',
        'video_url': data.get('video_url', ''),
        'lecture_file_id': data.get('lecture_file_id', ''),
        'text_content': data.get('text_content', ''),
        'order': lesson_order,
        'materials': []
    }
    
    try:
        success = add_lesson_to_module(course_slug, module_id, new_lesson)
        
        if success:
            # Формируем информацию о добавленном контенте
            content_info = []
            if new_lesson['video_url']:
                content_info.append("🎬 Видео")
            if new_lesson['lecture_file_id']:
                content_info.append("📄 PDF лекция")
            if new_lesson['text_content']:
                content_info.append("📝 Текст")
            
            content_text = ", ".join(content_info) if content_info else "Без контента"
            
            await message.answer(
                f"✅ <b>Урок успешно добавлен!</b>\n\n"
                f"📝 {new_lesson['title']}\n"
                f"📂 Модуль: {module['title']}\n"
                f"📦 Контент: {content_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить еще урок", callback_data=f"add_lesson_to_module_{course_slug}_{module_id}")],
                    [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"view_module_{course_slug}_{module_id}")]
                ])
            )
        else:
            await message.answer("❌ Ошибка при добавлении урока")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.clear()


# DEPRECATED: Старые обработчики редактирования уроков (с БД) закомментированы

@router.callback_query(F.data.startswith("edit_lessons_"))
async def edit_lessons_list(callback: CallbackQuery):
    """Список уроков для редактирования - DEPRECATED"""
    await callback.answer("⚠️ Используйте новый интерфейс через 'Управление курсами'", show_alert=True)
    return
    
    # СТАРЫЙ КОД ЗАКОММЕНТИРОВАН
    course_id = int(callback.data.split("_")[2])
    db: Session = get_db()
    
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        lessons = db.query(Lesson).filter(Lesson.course_id == course_id).order_by(
            Lesson.module_number, Lesson.lesson_number
        ).all()
        
        buttons = []
        for lesson in lessons:
            buttons.append([InlineKeyboardButton(
                text=f"М{lesson.module_number}.У{lesson.lesson_number}: {lesson.title}",
                callback_data=f"edit_lesson_{lesson.id}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="◀️ Назад к курсу",
            callback_data=f"manage_course_{course_id}"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"✏️ <b>Редактирование уроков курса \"{course.name}\"</b>\n\n"
            f"Выберите урок:",
            reply_markup=keyboard
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("edit_lesson_"))
async def edit_lesson_menu(callback: CallbackQuery):
    """Меню редактирования урока (новый формат с JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Новый формат: edit_lesson_{course_slug}_{module_id}_{lesson_id}
    parts = callback.data.split("_")
    
    # Проверяем формат - если старый (только число), показываем сообщение
    if len(parts) == 3:
        try:
            int(parts[2])  # Пытаемся преобразовать в число
            await callback.answer("⚠️ Используйте новый интерфейс через 'Управление курсами'", show_alert=True)
            return
        except ValueError:
            pass
    
    # Обработка нового формата
    if len(parts) < 5:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
        return
    
    course_slug = parts[2]
    module_id = parts[3]
    lesson_id = parts[4]
    
    from data import get_lesson_by_id
    
    lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
    
    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return
    
    text = f"✏️ <b>Редактирование урока</b>\n\n"
    text += f"📝 Название: {lesson['title']}\n"
    text += f"📄 Описание: {lesson.get('description', 'Не указано')[:100]}...\n\n"
    
    # Проверяем наличие контента
    has_video = bool(lesson.get('video_url'))
    has_lecture = bool(lesson.get('lecture_file_id'))
    has_text = bool(lesson.get('text_content'))
    
    text += f"🎬 Видео: {'✅ Есть' if has_video else '❌ Нет'}\n"
    text += f"📄 PDF лекция: {'✅ Есть' if has_lecture else '❌ Нет'}\n"
    text += f"📝 Текст: {'✅ Есть' if has_text else '❌ Нет'}\n"
    
    buttons = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_json_title_{course_slug}_{module_id}_{lesson_id}")],
        [InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"edit_json_desc_{course_slug}_{module_id}_{lesson_id}")],
        [InlineKeyboardButton(text="🎬 Изменить видео", callback_data=f"edit_json_video_{course_slug}_{module_id}_{lesson_id}")],
        [InlineKeyboardButton(text="📄 Изменить PDF лекцию", callback_data=f"edit_json_lecture_{course_slug}_{module_id}_{lesson_id}")],
        [InlineKeyboardButton(text="📝 Изменить текст", callback_data=f"edit_json_text_{course_slug}_{module_id}_{lesson_id}")],
        [InlineKeyboardButton(text="🗑 Удалить урок", callback_data=f"delete_json_lesson_{course_slug}_{module_id}_{lesson_id}")],
        [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"view_module_{course_slug}_{module_id}")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ===== РЕДАКТИРОВАНИЕ УРОКОВ (JSON ФОРМАТ) =====

@router.callback_query(F.data.startswith("edit_json_title_"))
async def edit_json_lesson_title_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия урока (JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[3]
    module_id = parts[4]
    lesson_id = parts[5]
    
    await state.update_data(course_slug=course_slug, module_id=module_id, lesson_id=lesson_id)
    await state.set_state(CourseManagement.editing_lesson_title)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование названия урока</b>\n\n"
        "Отправьте новое название:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_json_desc_"))
async def edit_json_lesson_desc_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования описания урока (JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[3]
    module_id = parts[4]
    lesson_id = parts[5]
    
    await state.update_data(course_slug=course_slug, module_id=module_id, lesson_id=lesson_id)
    await state.set_state(CourseManagement.editing_lesson_description)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование описания урока</b>\n\n"
        "Отправьте новое описание:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_json_video_"))
async def edit_json_lesson_video_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования видео урока (JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[3]
    module_id = parts[4]
    lesson_id = parts[5]
    
    await state.update_data(course_slug=course_slug, module_id=module_id, lesson_id=lesson_id)
    await state.set_state(CourseManagement.editing_lesson_video)
    
    await callback.message.edit_text(
        "🎬 <b>Редактирование видео урока</b>\n\n"
        "Отправьте новую ссылку на видео или '-' для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_json_lecture_"))
async def edit_json_lesson_lecture_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования PDF лекции урока (JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[3]
    module_id = parts[4]
    lesson_id = parts[5]
    
    # Очищаем state и устанавливаем данные для редактирования
    await state.clear()
    await state.update_data(
        course_slug=course_slug, 
        module_id=module_id, 
        lesson_id=lesson_id, 
        editing_lecture=True,
        adding_lesson=False  # явно указываем что это НЕ добавление
    )
    await state.set_state(CourseManagement.waiting_for_lesson_lecture_file)
    
    print(f"🎯 Начало редактирования PDF лекции для урока: {lesson_id}")
    
    await callback.message.edit_text(
        "📄 <b>Редактирование PDF лекции урока</b>\n\n"
        "Отправьте новый PDF файл или нажмите 'Удалить' для удаления существующей лекции:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить лекцию", callback_data=f"remove_lecture_{course_slug}_{module_id}_{lesson_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_lecture_"))
async def remove_json_lesson_lecture(callback: CallbackQuery, state: FSMContext):
    """Удаление PDF лекции из урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[2]
    module_id = parts[3]
    lesson_id = parts[4]
    
    from data import get_lesson_by_id, update_lesson
    
    lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
    if lesson:
        lesson['lecture_file_id'] = ""
        update_lesson(course_slug, module_id, lesson_id, lesson)
        
        await callback.answer("✅ PDF лекция удалена", show_alert=True)
        await state.clear()
        
        # Возвращаемся к редактированию урока - показываем меню заново
        text = f"✏️ <b>Редактирование урока</b>\n\n"
        text += f"📝 Название: {lesson['title']}\n"
        text += f"📄 Описание: {lesson.get('description', 'Не указано')[:100]}...\n\n"
        
        # Проверяем наличие контента
        has_video = bool(lesson.get('video_url'))
        has_lecture = False  # Мы только что удалили
        has_text = bool(lesson.get('text_content'))
        
        text += f"🎬 Видео: {'✅ Есть' if has_video else '❌ Нет'}\n"
        text += f"📄 PDF лекция: ❌ Нет\n"
        text += f"📝 Текст: {'✅ Есть' if has_text else '❌ Нет'}\n"
        
        buttons = [
            [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_json_title_{course_slug}_{module_id}_{lesson_id}")],
            [InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"edit_json_desc_{course_slug}_{module_id}_{lesson_id}")],
            [InlineKeyboardButton(text="🎬 Изменить видео", callback_data=f"edit_json_video_{course_slug}_{module_id}_{lesson_id}")],
            [InlineKeyboardButton(text="📄 Изменить PDF лекцию", callback_data=f"edit_json_lecture_{course_slug}_{module_id}_{lesson_id}")],
            [InlineKeyboardButton(text="📝 Изменить текст", callback_data=f"edit_json_text_{course_slug}_{module_id}_{lesson_id}")],
            [InlineKeyboardButton(text="🗑 Удалить урок", callback_data=f"delete_json_lesson_{course_slug}_{module_id}_{lesson_id}")],
            [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"view_module_{course_slug}_{module_id}")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.answer("❌ Урок не найден", show_alert=True)


@router.callback_query(F.data.startswith("edit_json_text_"))
async def edit_json_lesson_text_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования текста урока (JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[3]
    module_id = parts[4]
    lesson_id = parts[5]
    
    await state.update_data(course_slug=course_slug, module_id=module_id, lesson_id=lesson_id)
    await state.set_state(CourseManagement.editing_lesson_content)
    
    await callback.message.edit_text(
        "📝 <b>Редактирование текстового содержания урока</b>\n\n"
        "Отправьте новый текст или '-' для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_json_lesson_"))
async def delete_json_lesson_confirm(callback: CallbackQuery):
    """Подтверждение удаления урока (JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[3]
    module_id = parts[4]
    lesson_id = parts[5]
    
    from data import get_lesson_by_id
    
    lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
    
    if not lesson:
        await callback.answer("❌ Урок не найден", show_alert=True)
        return
    
    text = f"⚠️ <b>Удаление урока</b>\n\n"
    text += f"Вы уверены, что хотите удалить урок:\n"
    text += f"<b>{lesson['title']}</b>?\n\n"
    text += "Это действие нельзя отменить!"
    
    buttons = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_json_{course_slug}_{module_id}_{lesson_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_json_"))
async def delete_json_lesson_execute(callback: CallbackQuery):
    """Выполнение удаления урока (JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    course_slug = parts[3]
    module_id = parts[4]
    lesson_id = parts[5]
    
    from data import delete_lesson
    
    success = delete_lesson(course_slug, module_id, lesson_id)
    
    if success:
        await callback.answer("✅ Урок удален", show_alert=True)
        
        # Возвращаемся к модулю - показываем его заново
        from data import get_module_by_id, get_course_by_slug
        
        module = get_module_by_id(course_slug, module_id)
        course = get_course_by_slug(course_slug)
        
        if not module or not course:
            await callback.message.edit_text(
                "❌ Ошибка при загрузке модуля",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_course_{course_slug}")]
                ])
            )
            return
        
        text = f"📂 <b>{module['title']}</b>\n\n"
        if module.get('description'):
            text += f"{module['description']}\n\n"
        
        lessons = module.get('lessons', [])
        if lessons:
            text += f"📝 <b>Уроков: {len(lessons)}</b>\n\n"
            for i, lesson in enumerate(lessons, 1):
                text += f"{i}. {lesson.get('title', 'Без названия')}\n"
        else:
            text += "Уроков пока нет\n"
        
        buttons = []
        
        # Кнопки для редактирования уроков
        if lessons:
            for lesson in lessons:
                buttons.append([InlineKeyboardButton(
                    text=f"✏️ {lesson.get('title', 'Без названия')[:30]}...",
                    callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson['id']}"
                )])
        
        # Кнопка добавления урока
        buttons.append([InlineKeyboardButton(
            text="➕ Добавить урок",
            callback_data=f"add_lesson_to_module_{course_slug}_{module_id}"
        )])
        
        buttons.append([InlineKeyboardButton(
            text="◀️ К модулям",
            callback_data=f"view_modules_{course_slug}"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.answer("❌ Ошибка при удалении урока", show_alert=True)


# ===== ОБРАБОТЧИКИ СОХРАНЕНИЯ ИЗМЕНЕНИЙ =====

@router.message(CourseManagement.editing_lesson_title)
async def save_json_lesson_title(message: Message, state: FSMContext):
    """Сохранение нового названия урока (JSON)"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    lesson_id = data['lesson_id']
    
    from data import get_lesson_by_id, update_lesson
    
    lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
    if lesson:
        lesson['title'] = message.text.strip()
        update_lesson(course_slug, module_id, lesson_id, lesson)
        
        await message.answer(
            f"✅ Название урока обновлено!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К уроку", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
            ])
        )
    else:
        await message.answer("❌ Урок не найден")
    
    await state.clear()


@router.message(CourseManagement.editing_lesson_description)
async def save_json_lesson_description(message: Message, state: FSMContext):
    """Сохранение нового описания урока (JSON)"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    lesson_id = data['lesson_id']
    
    from data import get_lesson_by_id, update_lesson
    
    lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
    if lesson:
        lesson['description'] = message.text.strip()
        update_lesson(course_slug, module_id, lesson_id, lesson)
        
        await message.answer(
            f"✅ Описание урока обновлено!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К уроку", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
            ])
        )
    else:
        await message.answer("❌ Урок не найден")
    
    await state.clear()


@router.message(CourseManagement.editing_lesson_video)
async def save_json_lesson_video(message: Message, state: FSMContext):
    """Сохранение новой ссылки на видео урока (JSON)"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    lesson_id = data['lesson_id']
    
    from data import get_lesson_by_id, update_lesson
    
    lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
    if lesson:
        video_url = message.text.strip()
        lesson['video_url'] = "" if video_url == "-" else video_url
        update_lesson(course_slug, module_id, lesson_id, lesson)
        
        if video_url == "-":
            msg = "✅ Видео удалено из урока!"
        else:
            msg = "✅ Ссылка на видео обновлена!"
        
        await message.answer(
            msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К уроку", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
            ])
        )
    else:
        await message.answer("❌ Урок не найден")
    
    await state.clear()


@router.message(CourseManagement.waiting_for_lesson_lecture_file, F.document)
async def save_json_lesson_lecture(message: Message, state: FSMContext):
    """Сохранение PDF лекции урока (создание или редактирование)"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    
    # ОТЛАДКА: логируем данные
    logger.info(f"🔍 PDF Upload - State data: editing_lecture={data.get('editing_lecture')}, lesson_id={data.get('lesson_id')}, adding_lesson={data.get('adding_lesson')}")
    print(f"🔍 PDF Upload - State data: editing_lecture={data.get('editing_lecture')}, lesson_id={data.get('lesson_id')}, adding_lesson={data.get('adding_lesson')}")
    
    # Проверяем что это PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        await message.answer("❌ Пожалуйста, отправьте PDF файл")
        return
    
    # Проверяем, что это редактирование существующего урока, а не создание нового
    # Редактирование: есть editing_lecture И есть lesson_id И НЕТ adding_lesson
    if data.get('editing_lecture') and data.get('lesson_id') and not data.get('adding_lesson'):
        # ЭТО РЕДАКТИРОВАНИЕ СУЩЕСТВУЮЩЕГО УРОКА
        logger.info(f"✅ PDF Upload - РЕДАКТИРОВАНИЕ существующего урока: {data.get('lesson_id')}")
        print(f"✅ PDF Upload - РЕДАКТИРОВАНИЕ существующего урока: {data.get('lesson_id')}")
        course_slug = data['course_slug']
        module_id = data['module_id']
        lesson_id = data['lesson_id']
        
        from data import get_lesson_by_id, update_lesson
        
        lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
        if lesson:
            lesson['lecture_file_id'] = message.document.file_id
            update_lesson(course_slug, module_id, lesson_id, lesson)
            
            await message.answer(
                "✅ PDF лекция обновлена!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К уроку", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
                ])
            )
        else:
            await message.answer("❌ Урок не найден")
        
        await state.clear()
        return
    
    # Это создание нового урока - продолжаем процесс
    logger.info(f"➕ PDF Upload - СОЗДАНИЕ нового урока")
    print(f"➕ PDF Upload - СОЗДАНИЕ нового урока")
    await process_lesson_lecture(message, state)


@router.message(CourseManagement.editing_lesson_content)
async def save_json_lesson_text(message: Message, state: FSMContext):
    """Сохранение нового текста урока (JSON)"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    course_slug = data['course_slug']
    module_id = data['module_id']
    lesson_id = data['lesson_id']
    
    from data import get_lesson_by_id, update_lesson
    
    lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
    if lesson:
        text_content = message.text.strip()
        lesson['text_content'] = "" if text_content == "-" else text_content
        update_lesson(course_slug, module_id, lesson_id, lesson)
        
        if text_content == "-":
            msg = "✅ Текстовое содержание удалено из урока!"
        else:
            msg = "✅ Текстовое содержание урока обновлено!"
        
        await message.answer(
            msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К уроку", callback_data=f"edit_lesson_{course_slug}_{module_id}_{lesson_id}")]
            ])
        )
    else:
        await message.answer("❌ Урок не найден")
    
    await state.clear()


# ===== СТАРЫЕ ОБРАБОТЧИКИ ДЛЯ БД (DEPRECATED) =====

@router.callback_query(F.data.startswith("edit_title_"))
async def edit_lesson_title_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия (DEPRECATED - только для БД)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Проверяем, это старый формат (только число) или новый
    try:
        lesson_id = int(callback.data.split("_")[2])
        await callback.answer("⚠️ Используйте новый интерфейс через 'Управление курсами'", show_alert=True)
        return
    except:
        pass
    
    await state.update_data(editing_lesson_id=lesson_id)
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        await callback.message.edit_text(
            f"✏️ <b>Редактирование названия урока</b>\n\n"
            f"Текущее название: <b>{lesson.title}</b>\n\n"
            f"Отправьте новое название:",
            reply_markup=cancel_keyboard
        )
        
        await state.set_state(CourseManagement.editing_lesson_title)
    
    finally:
        db.close()
    
    await callback.answer()


@router.message(CourseManagement.editing_lesson_title)
async def edit_lesson_title_save(message: Message, state: FSMContext):
    """Сохранение нового названия"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    lesson_id = data['editing_lesson_id']
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        lesson.title = message.text.strip()
        db.commit()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к уроку", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        await message.answer(
            f"✅ Название урока обновлено!\n\n"
            f"Новое название: <b>{lesson.title}</b>",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("edit_desc_"))
async def edit_lesson_desc_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования описания"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    lesson_id = int(callback.data.split("_")[2])
    await state.update_data(editing_lesson_id=lesson_id)
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        current_desc = lesson.description if lesson.description else "Не указано"
        
        await callback.message.edit_text(
            f"✏️ <b>Редактирование описания урока</b>\n\n"
            f"Текущее описание:\n{current_desc}\n\n"
            f"Отправьте новое описание:",
            reply_markup=cancel_keyboard
        )
        
        await state.set_state(CourseManagement.editing_lesson_description)
    
    finally:
        db.close()
    
    await callback.answer()


@router.message(CourseManagement.editing_lesson_description)
async def edit_lesson_desc_save(message: Message, state: FSMContext):
    """Сохранение нового описания"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    lesson_id = data['editing_lesson_id']
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        lesson.description = message.text.strip()
        db.commit()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к уроку", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        await message.answer(
            "✅ Описание урока обновлено!",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("edit_content_"))
async def edit_lesson_content_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования контента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    lesson_id = int(callback.data.split("_")[2])
    await state.update_data(editing_lesson_id=lesson_id)
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        await callback.message.edit_text(
            f"✏️ <b>Редактирование контента урока</b>\n\n"
            f"Отправьте новый текст урока:",
            reply_markup=cancel_keyboard
        )
        
        await state.set_state(CourseManagement.editing_lesson_content)
    
    finally:
        db.close()
    
    await callback.answer()


@router.message(CourseManagement.editing_lesson_content)
async def edit_lesson_content_save(message: Message, state: FSMContext):
    """Сохранение нового контента"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    lesson_id = data['editing_lesson_id']
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        lesson.content = message.text.strip()
        db.commit()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к уроку", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        await message.answer(
            "✅ Контент урока обновлен!",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("edit_video_"))
async def edit_lesson_video_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования видео"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    lesson_id = int(callback.data.split("_")[2])
    await state.update_data(editing_lesson_id=lesson_id)
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        current_video = lesson.video_url if lesson.video_url else "Не указано"
        
        await callback.message.edit_text(
            f"✏️ <b>Редактирование видео урока</b>\n\n"
            f"Текущее видео: {current_video}\n\n"
            f"Отправьте новую ссылку на видео:",
            reply_markup=cancel_keyboard
        )
        
        await state.set_state(CourseManagement.editing_lesson_video)
    
    finally:
        db.close()
    
    await callback.answer()


@router.message(CourseManagement.editing_lesson_video)
async def edit_lesson_video_save(message: Message, state: FSMContext):
    """Сохранение нового видео"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    lesson_id = data['editing_lesson_id']
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        lesson.video_url = message.text.strip()
        db.commit()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к уроку", callback_data=f"edit_lesson_{lesson_id}")]
        ])
        
        await message.answer(
            "✅ Ссылка на видео обновлена!",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("delete_lesson_"))
async def delete_lesson_confirm(callback: CallbackQuery):
    """Подтверждение удаления урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    lesson_id = int(callback.data.split("_")[2])
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        buttons = [
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{lesson_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_lesson_{lesson_id}")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы действительно хотите удалить урок?\n\n"
            f"📍 М{lesson.module_number}.У{lesson.lesson_number}: {lesson.title}\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=keyboard
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_lesson(callback: CallbackQuery):
    """Удаление урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    lesson_id = int(callback.data.split("_")[2])
    
    db: Session = get_db()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        course_id = lesson.course_id
        
        db.delete(lesson)
        db.commit()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к курсу", callback_data=f"manage_course_{course_id}")]
        ])
        
        await callback.message.edit_text(
            "✅ <b>Урок успешно удален!</b>",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "download_analytics")
async def download_analytics(callback: CallbackQuery):
    """Генерация и отправка Excel файла с аналитикой"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer("⏳ Генерирую файл...")
    
    db: Session = get_db()
    
    try:
        # Импортируем функции для работы с данными
        from data import get_all_guides
        
        # Создаем Excel файл
        wb = Workbook()
        
        # Лист 1: Общая статистика
        ws_stats = wb.active
        ws_stats.title = "Общая статистика"
        
        # Заголовки
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        
        ws_stats['A1'] = 'Общая статистика бота'
        ws_stats['A1'].font = Font(bold=True, size=14)
        ws_stats.merge_cells('A1:B1')
        
        row = 3
        ws_stats[f'A{row}'] = 'Показатель'
        ws_stats[f'B{row}'] = 'Значение'
        ws_stats[f'A{row}'].fill = header_fill
        ws_stats[f'B{row}'].fill = header_fill
        ws_stats[f'A{row}'].font = header_font
        ws_stats[f'B{row}'].font = header_font
        
        # Данные
        total_users = db.query(User).count()
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)
        
        active_week = db.query(User).filter(User.last_activity >= week_ago).count()
        active_month = db.query(User).filter(User.last_activity >= month_ago).count()
        new_week = db.query(User).filter(User.created_at >= week_ago).count()
        new_month = db.query(User).filter(User.created_at >= month_ago).count()
        
        total_payments = db.query(Payment).filter(Payment.status == 'succeeded').count()
        total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == 'succeeded').scalar() or 0
        week_payments = db.query(Payment).filter(
            Payment.status == 'succeeded',
            Payment.created_at >= week_ago
        ).count()
        week_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.status == 'succeeded',
            Payment.created_at >= week_ago
        ).scalar() or 0
        month_payments = db.query(Payment).filter(
            Payment.status == 'succeeded',
            Payment.created_at >= month_ago
        ).count()
        month_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.status == 'succeeded',
            Payment.created_at >= month_ago
        ).scalar() or 0
        
        stats_data = [
            ('ПОЛЬЗОВАТЕЛИ', ''),
            ('Всего пользователей', total_users),
            ('Активных за неделю', active_week),
            ('Активных за месяц', active_month),
            ('Новых за неделю', new_week),
            ('Новых за месяц', new_month),
            ('', ''),
            ('ФИНАНСЫ', ''),
            ('Всего покупок', total_payments),
            ('Общая выручка, ₽', f'{total_revenue:,.2f}'),
            ('Покупок за неделю', week_payments),
            ('Выручка за неделю, ₽', f'{week_revenue:,.2f}'),
            ('Покупок за месяц', month_payments),
            ('Выручка за месяц, ₽', f'{month_revenue:,.2f}'),
            ('', ''),
            ('КОНТЕНТ', ''),
            ('Курсов', len(get_all_courses())),
            ('Консультаций', len(get_all_consultations())),
            ('Гайдов', len(get_all_guides())),
        ]
        
        row = 4
        for label, value in stats_data:
            ws_stats[f'A{row}'] = label
            ws_stats[f'B{row}'] = value
            if label and not value:
                ws_stats[f'A{row}'].font = Font(bold=True)
            row += 1
        
        # Автоширина колонок
        ws_stats.column_dimensions['A'].width = 30
        ws_stats.column_dimensions['B'].width = 20
        
        # Лист 2: Пользователи
        ws_users = wb.create_sheet("Пользователи")
        
        headers = ['ID', 'Telegram ID', 'Username', 'Имя', 'Фамилия', 'Дата регистрации', 'Последняя активность', 'Покупок']
        for col, header in enumerate(headers, 1):
            cell = ws_users.cell(1, col, header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        users = db.query(User).order_by(User.created_at.desc()).all()
        
        for row, user in enumerate(users, 2):
            payments_count = db.query(Payment).filter(
                Payment.user_id == user.id,
                Payment.status == 'succeeded'
            ).count()
            
            ws_users.cell(row, 1, user.id)
            ws_users.cell(row, 2, user.telegram_id)
            ws_users.cell(row, 3, user.username or '-')
            ws_users.cell(row, 4, user.first_name or '-')
            ws_users.cell(row, 5, user.last_name or '-')
            ws_users.cell(row, 6, user.created_at.strftime('%d.%m.%Y %H:%M'))
            ws_users.cell(row, 7, user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else '-')
            ws_users.cell(row, 8, payments_count)
        
        # Автоширина
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            ws_users.column_dimensions[col].width = 15
        
        # Лист 3: Покупки
        ws_payments = wb.create_sheet("Покупки")
        
        headers = ['ID', 'Пользователь', 'Продукт', 'Сумма, ₽', 'Статус', 'Дата создания', 'Дата оплаты']
        for col, header in enumerate(headers, 1):
            cell = ws_payments.cell(1, col, header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        payments = db.query(Payment).order_by(Payment.created_at.desc()).all()
        
        for row, payment in enumerate(payments, 2):
            user = payment.user
            username = user.username if user.username else f"{user.first_name or 'Пользователь'}"
            
            product_name = '-'
            # Определяем тип продукта и название из новой структуры
            from data import get_course_by_slug, get_consultation_by_slug, get_guide_by_id
            
            if payment.product_type == 'course' and payment.course_slug:
                course = get_course_by_slug(payment.course_slug)
                product_name = f"Курс: {course['name']}" if course else "Курс"
            elif payment.product_type == 'consultation' and payment.consultation_slug:
                consultation = get_consultation_by_slug(payment.consultation_slug)
                product_name = f"Консультация: {consultation['name']}" if consultation else "Консультация"
            elif payment.product_type == 'guide' and payment.product_id:
                guide = get_guide_by_id(payment.product_id)
                product_name = f"Гайд: {guide['name']}" if guide else "Гайд"
            else:
                product_name = payment.product_type or "Неизвестно"
            
            ws_payments.cell(row, 1, payment.id)
            ws_payments.cell(row, 2, username)
            ws_payments.cell(row, 3, product_name)
            ws_payments.cell(row, 4, payment.amount)
            ws_payments.cell(row, 5, payment.status)
            ws_payments.cell(row, 6, payment.created_at.strftime('%d.%m.%Y %H:%M'))
            ws_payments.cell(row, 7, payment.paid_at.strftime('%d.%m.%Y %H:%M') if payment.paid_at else '-')
        
        # Автоширина
        for col, width in zip(['A', 'B', 'C', 'D', 'E', 'F', 'G'], [8, 20, 30, 12, 12, 18, 18]):
            ws_payments.column_dimensions[col].width = width
        
        # Сохраняем в буфер
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Генерируем имя файла с датой
        filename = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Сохраняем временно
        temp_path = f"/tmp/{filename}"
        with open(temp_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Отправляем файл
        await callback.message.answer_document(
            document=FSInputFile(temp_path, filename=filename),
            caption="📊 <b>Детальная аналитика</b>\n\n"
                   "Файл содержит:\n"
                   "• Общую статистику\n"
                   "• Список всех пользователей\n"
                   "• Все покупки"
        )
        
        # Удаляем временный файл
        os.remove(temp_path)
        
        await callback.answer("✅ Файл отправлен!")
    
    except Exception as e:
        await callback.answer(f"Ошибка при генерации: {str(e)}", show_alert=True)
    
    finally:
        db.close()


@router.callback_query(F.data == "admin_consultations")
async def show_consultations_management(callback: CallbackQuery):
    """Показать управление консультациями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    consultations = get_all_consultations()
    
    if not consultations:
        await callback.message.edit_text(
            "🔮 <b>Консультации отсутствуют</b>\n\n"
            "Консультации хранятся в data/consultations.json",
            reply_markup=get_back_to_admin_keyboard()
        )
    else:
        buttons = []
        for cons in consultations:
            # Определяем текст цены
            if cons.get('options'):
                price_text = "Варианты"
            elif cons.get('price'):
                price_text = f"{cons['price']:,.0f} ₽"
            else:
                price_text = "Цена не указана"
            
            status_emoji = "✅" if cons.get('is_active', True) else "❌"
            buttons.append([InlineKeyboardButton(
                text=f"{cons.get('emoji', '🔮')} {cons['name']} ({price_text}) {status_emoji}",
                callback_data=f"manage_consultation_{cons['slug']}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="◀️ Назад в админ-панель",
            callback_data="admin_panel"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            "🔮 <b>Управление консультациями</b>\n\n"
            "Просмотр консультаций. Для редактирования используйте файл data/consultations.json",
            reply_markup=keyboard
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("manage_consultation_"))
async def manage_consultation(callback: CallbackQuery):
    """Просмотр конкретной консультации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    from data import get_consultation_by_slug
    
    cons_slug = callback.data.replace("manage_consultation_", "")
    cons = get_consultation_by_slug(cons_slug)
    
    if not cons:
        await callback.answer("Консультация не найдена", show_alert=True)
        return
    
    text = f"🔮 <b>{cons['name']}</b>\n\n"
    text += f"📍 Slug: <code>{cons['slug']}</code>\n"
    
    if cons.get('price'):
        text += f"💰 Цена: {cons['price']:,.0f} ₽\n"
    
    if cons.get('duration'):
        text += f"⏱ Длительность: {cons['duration']}\n"
    
    if cons.get('category'):
        text += f"📂 Категория: {cons['category']}\n"
    
    text += f"✅ Активна: {'Да' if cons.get('is_active', True) else 'Нет'}\n"
    
    if cons.get('options'):
        text += f"\n📋 Вариантов: {len(cons['options'])}\n"
        for opt in cons['options']:
            if opt.get('is_active', True):
                text += f"  • {opt['name']}: {opt['price']:,.0f} ₽\n"
    
    text += "\n\n<i>Для редактирования измените data/consultations.json</i>"
    
    buttons = [
        [InlineKeyboardButton(text="◀️ Назад к консультациям", callback_data="admin_consultations")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_cons_"))
async def toggle_consultation(callback: CallbackQuery):
    """Переключить активность консультации - заглушка"""
    await callback.answer("⚠️ Редактирование через data/consultations.json", show_alert=True)


# Редактирование консультаций через JSON файлы

@router.callback_query(F.data.startswith("edit_cons_"))
async def edit_consultation_help(callback: CallbackQuery):
    """Информация о редактировании консультаций"""
    await callback.message.answer(
        "ℹ️ <b>Редактирование консультаций</b>\n\n"
        "Консультации хранятся в файле:\n"
        "<code>data/consultations.json</code>\n\n"
        "Для редактирования:\n"
        "1. Откройте файл в редакторе\n"
        "2. Измените нужные поля\n"
        "3. Сохраните файл\n"
        "4. Перезапустите бота\n\n"
        "📝 Доступные поля:\n"
        "• name - название\n"
        "• price - цена\n"
        "• duration - длительность\n"
        "• description - описание\n"
        "• is_active - активна/неактивна\n"
        "• options - варианты консультации"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("create_consultation"))
async def create_consultation_help(callback: CallbackQuery):
    """Информация о создании консультаций"""
    await callback.message.edit_text(
        "ℹ️ <b>Создание консультации</b>\n\n"
        "Консультации хранятся в файле:\n"
        "<code>data/consultations.json</code>\n\n"
        "Для создания новой консультации:\n"
        "1. Откройте файл в редакторе\n"
        "2. Скопируйте структуру существующей консультации\n"
        "3. Измените поля под новую консультацию\n"
        "4. Не забудьте уникальный slug\n"
        "5. Сохраните файл\n"
        "6. Перезапустите бота\n\n"
        "📋 Пример структуры в документации DATA_MANAGEMENT.md",
        reply_markup=get_back_to_admin_keyboard()
    )
    await callback.answer()


# Управление гайдами вынесено в отдельный модуль handlers/admin_guides.py


@router.callback_query(F.data == "create_course")
async def create_course_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания нового курса"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_courses")]
    ])
    
    await callback.message.edit_text(
        "➕ <b>Создание нового курса</b>\n\n"
        "Шаг 1/4: Введите название курса:",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(CourseCreation.waiting_for_name)
    await callback.answer()


@router.message(CourseCreation.waiting_for_name)
async def create_course_name(message: Message, state: FSMContext):
    """Получение названия курса"""
    if not is_admin(message.from_user.id):
        return
    
    await state.update_data(course_name=message.text.strip())
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_courses")]
    ])
    
    await message.answer(
        f"✅ Название: <b>{message.text.strip()}</b>\n\n"
        f"Шаг 2/4: Введите slug курса (для URL, например: astro-basics):",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(CourseCreation.waiting_for_slug)


@router.message(CourseCreation.waiting_for_slug)
async def create_course_slug(message: Message, state: FSMContext):
    """Получение slug курса"""
    if not is_admin(message.from_user.id):
        return
    
    slug = message.text.strip().lower().replace(' ', '-')
    
    # Проверяем уникальность slug
    db: Session = get_db()
    try:
        existing = db.query(Course).filter(Course.slug == slug).first()
        if existing:
            await message.answer("❌ Курс с таким slug уже существует. Введите другой slug:")
            return
    finally:
        db.close()
    
    await state.update_data(course_slug=slug)
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_courses")]
    ])
    
    await message.answer(
        f"✅ Slug: <code>{slug}</code>\n\n"
        f"Шаг 3/4: Введите описание курса:",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(CourseCreation.waiting_for_description)


@router.message(CourseCreation.waiting_for_description)
async def create_course_description(message: Message, state: FSMContext):
    """Получение описания курса"""
    if not is_admin(message.from_user.id):
        return
    
    await state.update_data(course_description=message.text.strip())
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_courses")]
    ])
    
    await message.answer(
        f"✅ Описание сохранено\n\n"
        f"Шаг 4/4: Введите длительность курса (например: 3 месяца):",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(CourseCreation.waiting_for_duration)


@router.message(CourseCreation.waiting_for_duration)
async def create_course_save(message: Message, state: FSMContext):
    """Сохранение нового курса"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    
    db: Session = get_db()
    try:
        # Получаем максимальный order
        max_order = db.query(func.max(Course.order)).scalar() or 0
        
        new_course = Course(
            name=data['course_name'],
            slug=data['course_slug'],
            description=data['course_description'],
            short_description=data['course_description'][:200],  # Первые 200 символов
            duration=message.text.strip(),
            is_active=True,
            order=max_order + 1
        )
        
        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить урок", callback_data=f"add_lesson_{new_course.id}")],
            [InlineKeyboardButton(text="◀️ К списку курсов", callback_data="admin_courses")]
        ])
        
        await message.answer(
            f"✅ <b>Курс успешно создан!</b>\n\n"
            f"📖 {new_course.name}\n"
            f"🔗 Slug: <code>{new_course.slug}</code>\n"
            f"⏱ Длительность: {new_course.duration}\n\n"
            f"Теперь вы можете добавить уроки в курс.",
            reply_markup=back_keyboard
        )
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании курса: {str(e)}")
    
    finally:
        db.close()
        await state.clear()


# ==================== СОЗДАНИЕ ПЛАТЕЖНОЙ ССЫЛКИ ====================

@router.callback_query(F.data == "admin_create_payment_link")
async def admin_create_payment_link(callback: CallbackQuery, state: FSMContext):
    """Начало создания платежной ссылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    await callback.message.edit_text(
        "💳 <b>Создание платежной ссылки</b>\n\n"
        "Введите Telegram username пользователя (с @):\n\n"
        "<i>Например: @username или 123456789</i>",
        reply_markup=get_back_to_admin_keyboard()
    )
    
    await state.set_state(PaymentLinkCreation.waiting_for_user_id)
    await callback.answer()


@router.message(StateFilter(PaymentLinkCreation.waiting_for_user_id))
async def process_user_id(message: Message, state: FSMContext):
    """Обработка ввода ID пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    user_input = message.text.strip()
    db = await get_db()
    user_repo = UserRepository(db)
    
    # Проверяем, это ID или username
    if user_input.startswith('@'):
        username = user_input[1:]  # Убираем @
        user = await user_repo.get_by_username(username)
    else:
        try:
            telegram_id = int(user_input)
            user = await user_repo.get_by_telegram_id(telegram_id)
        except ValueError:
            await message.answer("❌ Неверный формат. Введите числовой ID или username с @")
            return
    
    if not user:
        await message.answer(
            "❌ Пользователь не найден в базе.\n\n"
            "Убедитесь, что пользователь хотя бы раз запускал бота."
        )
        return
    
    # Сохраняем данные пользователя
    await state.update_data(
        user_id=str(user.id),
        telegram_id=user.telegram_id,
        user_name=user.first_name or user.username or f"ID{user.telegram_id}"
    )
    
    # Сохраняем тип продукта как консультация
    await state.update_data(product_type='consultation')
    
    # Показываем список консультаций сразу
    consultations = get_all_consultations()
    
    if not consultations:
        await message.answer(
            "❌ Нет доступных консультаций",
            reply_markup=get_back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    buttons = []
    for cons in consultations:
        buttons.append([InlineKeyboardButton(
            text=f"{cons.get('emoji', '🔮')} {cons['name']}",
            callback_data=f"paylink_cons_{cons['slug']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        f"✅ Пользователь найден: <b>{user.first_name or user.username or 'Пользователь'}</b>\n"
        f"ID: <code>{user.telegram_id}</code>\n\n"
        "🔮 Выберите консультацию:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("paylink_cons_"))
async def process_consultation_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора консультации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    from data import get_consultation_by_slug
    
    cons_slug = callback.data.replace("paylink_cons_", "")
    consultation = get_consultation_by_slug(cons_slug)
    
    if not consultation:
        await callback.answer("❌ Консультация не найдена", show_alert=True)
        return
    
    await state.update_data(
        consultation_slug=cons_slug,
        consultation_name=consultation['name']
    )
    
    # Если есть варианты - показываем их
    options = consultation.get('options', [])
    
    if options:
        buttons = []
        for option in options:
            if option.get('is_active', True):
                buttons.append([InlineKeyboardButton(
                    text=f"{option['name']} - {option['price']:,.0f} ₽",
                    callback_data=f"paylink_option_{option['id']}"
                )])
        
        buttons.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"🔮 {consultation['name']}\n\n"
            "Выберите вариант:",
            reply_markup=keyboard
        )
    elif consultation.get('price'):
        # Есть фиксированная цена - используем её автоматически
        await state.update_data(amount=consultation['price'])
        
        # Показываем подтверждение и сразу создаем платеж
        await callback.message.edit_text(
            f"🔮 {consultation['name']}\n\n"
            f"💰 Стоимость: {consultation['price']:,.0f} ₽\n\n"
            f"⏳ Создаю платежную ссылку...",
            reply_markup=None
        )
        
        # Создаем платеж
        await create_payment_link(callback.message, state)
    else:
        # Нет ни вариантов, ни цены - просим ввести сумму вручную
        await callback.message.edit_text(
            f"🔮 {consultation['name']}\n\n"
            "Введите стоимость в рублях:\n\n"
            "<i>Например: 5000</i>",
            reply_markup=get_back_to_admin_keyboard()
        )
        await state.set_state(PaymentLinkCreation.waiting_for_amount)
    
    await callback.answer()


@router.callback_query(F.data.startswith("paylink_option_"))
async def process_option_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора варианта консультации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    from data import get_consultation_by_slug, get_consultation_option
    
    option_id = callback.data.replace("paylink_option_", "")
    
    data = await state.get_data()
    consultation_slug = data.get('consultation_slug')
    consultation = get_consultation_by_slug(consultation_slug)
    
    if not consultation:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    option = get_consultation_option(consultation_slug, option_id)
    
    if not option:
        await callback.answer("❌ Вариант не найден", show_alert=True)
        return
    
    await state.update_data(
        consultation_option_id=option_id,
        amount=option['price'],
        option_name=option['name']
    )
    
    # Создаем платеж
    await create_payment_link(callback.message, state)
    await callback.answer()


@router.message(StateFilter(PaymentLinkCreation.waiting_for_amount))
async def process_amount(message: Message, state: FSMContext):
    """Обработка ввода суммы"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        amount = float(message.text.strip().replace(',', '.').replace(' ', ''))
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        await state.update_data(amount=amount)
        
        # Создаем платеж
        await create_payment_link(message, state)
    
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Введите число (например: 5000)")


async def create_payment_link(message: Message, state: FSMContext):
    """Создание платежной ссылки и платежа в БД"""
    from payments import YooKassaPayment
    
    data = await state.get_data()
    
    user_id_str = data.get('user_id')
    telegram_id = data.get('telegram_id')
    user_name = data.get('user_name')
    product_type = data.get('product_type')
    amount = data.get('amount')
    
    db = await get_db()
    payment_repo = PaymentRepository(db)
    
    try:
        # Формируем описание
        if product_type == 'consultation':
            description = f"Консультация: {data.get('consultation_name')}"
            if data.get('option_name'):
                description += f" - {data.get('option_name')}"
        elif product_type == 'course':
            description = f"Курс: {data.get('course_name')}"
            if data.get('tariff_name'):
                description += f" - {data.get('tariff_name')}"
        elif product_type == 'guide':
            description = f"Гайд: {data.get('guide_name', 'Гайд')}"
        else:
            description = "Продукт"
        
        # Создаем платеж в БД
        payment = Payment(
            user_id=ObjectId(user_id_str),
            amount=amount,
            status='pending',
            product_type=product_type,
            is_payment_link=True  # Помечаем как платеж по ссылке
        )
        
        if product_type == 'consultation':
            payment.consultation_slug = data.get('consultation_slug')
            payment.consultation_option_id = data.get('consultation_option_id')
        elif product_type == 'course':
            payment.course_slug = data.get('course_slug')
            payment.tariff_id = data.get('tariff_id')
        elif product_type == 'guide':
            payment.product_id = data.get('guide_id', 'guide-custom')
        
        payment = await payment_repo.create(payment)
        
        # Создаем платеж в YooKassa
        yookassa = YooKassaPayment()
        
        bot_info = await message.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}" if bot_info.username else "https://t.me"
        
        payment_result = yookassa.create_payment(
            amount=amount,
            description=description,
            return_url=return_url,
            metadata={
                'payment_db_id': str(payment.id),
                'user_telegram_id': telegram_id
            }
        )
        
        if not payment_result:
            await payment_repo.update(payment.id, {"status": "failed"})
            await message.answer(
                "❌ Ошибка при создании платежа в YooKassa",
                reply_markup=get_back_to_admin_keyboard()
            )
            await state.clear()
            return
        
        # Обновляем платеж
        await payment_repo.update(payment.id, {
            "payment_id": payment_result['id'],
            "confirmation_url": payment_result['confirmation_url']
        })
        
        # Отправляем ссылку админу
        await message.answer(
            f"✅ <b>Платежная ссылка создана!</b>\n\n"
            f"👤 Пользователь: {user_name}\n"
            f"💰 Сумма: {amount:,.0f} ₽\n"
            f"📦 Продукт: {description}\n\n"
            f"🔗 Ссылка на оплату:\n"
            f"<code>{payment_result['confirmation_url']}</code>\n\n"
            f"<i>Отправьте эту ссылку пользователю для оплаты</i>",
            reply_markup=get_back_to_admin_keyboard()
        )
        
        await state.clear()
    
    except Exception as e:
        await message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_to_admin_keyboard()
        )
        await state.clear()


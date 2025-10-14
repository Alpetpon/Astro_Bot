from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from config import config
from database import get_db, User, Payment
from keyboards import get_admin_keyboard, get_back_to_admin_keyboard
from data import get_all_courses, get_all_consultations

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


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id == config.ADMIN_ID


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


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        # Общая статистика
        total_users = db.query(User).count()
        total_purchases = db.query(Payment).count()
        total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0
        
        # Активные пользователи (за последние 7 дней)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users = db.query(User).filter(User.last_activity >= week_ago).count()
        
        # Новые пользователи за неделю
        new_users = db.query(User).filter(User.created_at >= week_ago).count()
        
        # Покупки за неделю
        week_purchases = db.query(Payment).filter(Payment.created_at >= week_ago).count()
        week_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.created_at >= week_ago
        ).scalar() or 0
        
        # Курсы и консультации (из JSON)
        total_courses = len(get_all_courses())
        total_consultations = len(get_all_consultations())
        
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
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def broadcast_info(callback: CallbackQuery):
    """Информация о рассылке"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Для отправки рассылки всем пользователям используйте команду:\n"
        "<code>/broadcast [текст сообщения]</code>\n\n"
        "Пример:\n"
        "<code>/broadcast Новый курс уже доступен!</code>",
        reply_markup=get_back_to_admin_keyboard()
    )
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
    
    db: Session = get_db()
    
    try:
        # Получаем всех пользователей
        users = db.query(User).all()
        
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
            except Exception as e:
                fail_count += 1
        
        await status_msg.edit_text(
            f"✅ Рассылка завершена!\n\n"
            f"Успешно: {success_count}\n"
            f"Ошибок: {fail_count}"
        )
    
    finally:
        db.close()


@router.callback_query(F.data == "admin_courses")
async def show_courses_management(callback: CallbackQuery):
    """Показать управление курсами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        courses = db.query(Course).order_by(Course.order).all()
        
        if not courses:
            await callback.message.edit_text(
                "📚 <b>Курсы отсутствуют</b>\n\n"
                "Создайте курсы через utils/admin.py",
                reply_markup=get_back_to_admin_keyboard()
            )
        else:
            buttons = []
            for course in courses:
                lessons_count = len(course.lessons)
                buttons.append([InlineKeyboardButton(
                    text=f"📖 {course.name} ({lessons_count} уроков)",
                    callback_data=f"manage_course_{course.id}"
                )])
            
            buttons.append([InlineKeyboardButton(
                text="➕ Создать новый курс",
                callback_data="create_course"
            )])
            buttons.append([InlineKeyboardButton(
                text="◀️ Назад в админ-панель",
                callback_data="admin_panel"
            )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(
                "📚 <b>Управление курсами</b>\n\n"
                "Выберите курс для редактирования или создайте новый:",
                reply_markup=keyboard
            )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("manage_course_"))
async def manage_course(callback: CallbackQuery):
    """Управление конкретным курсом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    course_id = int(callback.data.split("_")[2])
    db: Session = get_db()
    
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not course:
            await callback.answer("Курс не найден", show_alert=True)
            return
        
        lessons = db.query(Lesson).filter(Lesson.course_id == course_id).order_by(
            Lesson.module_number, Lesson.lesson_number
        ).all()
        
        text = f"📖 <b>{course.name}</b>\n\n"
        
        if lessons:
            text += "📝 <b>Уроки:</b>\n\n"
            for lesson in lessons:
                text += f"• М{lesson.module_number}.У{lesson.lesson_number}: {lesson.title}\n"
        else:
            text += "Уроков пока нет\n"
        
        buttons = [
            [InlineKeyboardButton(
                text="➕ Добавить урок",
                callback_data=f"add_lesson_{course_id}"
            )]
        ]
        
        if lessons:
            buttons.append([InlineKeyboardButton(
                text="✏️ Редактировать урок",
                callback_data=f"edit_lessons_{course_id}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="◀️ Назад к курсам",
            callback_data="admin_courses"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("add_lesson_"))
async def add_lesson_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    course_id = int(callback.data.split("_")[2])
    
    # Сохраняем course_id в состоянии
    await state.update_data(course_id=course_id)
    
    # Получаем номер следующего урока
    db: Session = get_db()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
        
        if lessons:
            max_module = max(lesson.module_number for lesson in lessons)
            max_lesson_in_module = max(
                lesson.lesson_number for lesson in lessons 
                if lesson.module_number == max_module
            )
            suggested_module = max_module
            suggested_lesson = max_lesson_in_module + 1
        else:
            suggested_module = 1
            suggested_lesson = 1
        
        await state.update_data(
            suggested_module=suggested_module,
            suggested_lesson=suggested_lesson
        )
        
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_course_{course_id}")]
        ])
        
        await callback.message.edit_text(
            f"➕ <b>Добавление урока в курс \"{course.name}\"</b>\n\n"
            f"Предлагаю: Модуль {suggested_module}, Урок {suggested_lesson}\n\n"
            f"Отправьте название урока в формате:\n"
            f"<code>М.У Название</code>\n\n"
            f"Например: <code>{suggested_module}.{suggested_lesson} Введение в астрологию</code>\n"
            f"Или просто: <code>Введение в астрологию</code> (будет М{suggested_module}.У{suggested_lesson})",
            reply_markup=cancel_keyboard
        )
        
        await state.set_state(CourseManagement.waiting_for_lesson_title)
    
    finally:
        db.close()
    
    await callback.answer()


@router.message(CourseManagement.waiting_for_lesson_title)
async def add_lesson_title(message: Message, state: FSMContext):
    """Получение названия урока"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    course_id = data['course_id']
    suggested_module = data['suggested_module']
    suggested_lesson = data['suggested_lesson']
    
    title_text = message.text.strip()
    
    # Парсим модуль и урок, если указаны
    if '.' in title_text.split()[0]:
        try:
            module_lesson, *title_parts = title_text.split(maxsplit=1)
            module_num, lesson_num = map(int, module_lesson.split('.'))
            title = title_parts[0] if title_parts else "Без названия"
        except:
            module_num = suggested_module
            lesson_num = suggested_lesson
            title = title_text
    else:
        module_num = suggested_module
        lesson_num = suggested_lesson
        title = title_text
    
    await state.update_data(
        lesson_title=title,
        module_number=module_num,
        lesson_number=lesson_num
    )
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_course_{course_id}")]
    ])
    
    await message.answer(
        f"✅ Название: <b>{title}</b>\n"
        f"📍 Позиция: Модуль {module_num}, Урок {lesson_num}\n\n"
        f"Теперь отправьте описание урока:",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(CourseManagement.waiting_for_lesson_description)


@router.message(CourseManagement.waiting_for_lesson_description)
async def add_lesson_description(message: Message, state: FSMContext):
    """Получение описания урока"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    course_id = data['course_id']
    
    await state.update_data(lesson_description=message.text.strip())
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_course_{course_id}")]
    ])
    
    await message.answer(
        "✅ Описание сохранено\n\n"
        "Теперь отправьте контент урока (текст урока):",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(CourseManagement.waiting_for_lesson_content)


@router.message(CourseManagement.waiting_for_lesson_content)
async def add_lesson_content(message: Message, state: FSMContext):
    """Получение контента урока"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    course_id = data['course_id']
    
    await state.update_data(lesson_content=message.text.strip())
    
    skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_video_{course_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_course_{course_id}")]
    ])
    
    await message.answer(
        "✅ Контент сохранен\n\n"
        "Отправьте ссылку на видео (YouTube, Vimeo и т.д.) или нажмите 'Пропустить':",
        reply_markup=skip_keyboard
    )
    
    await state.set_state(CourseManagement.waiting_for_lesson_video)


@router.callback_query(F.data.startswith("skip_video_"))
async def skip_video(callback: CallbackQuery, state: FSMContext):
    """Пропустить видео и сохранить урок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await save_new_lesson(callback.message, state, video_url=None)
    await callback.answer()


@router.message(CourseManagement.waiting_for_lesson_video)
async def add_lesson_video(message: Message, state: FSMContext):
    """Получение видео для урока"""
    if not is_admin(message.from_user.id):
        return
    
    video_url = message.text.strip()
    await save_new_lesson(message, state, video_url)


async def save_new_lesson(message: Message, state: FSMContext, video_url: str = None):
    """Сохранение нового урока в БД"""
    data = await state.get_data()
    
    db: Session = get_db()
    try:
        lesson = Lesson(
            course_id=data['course_id'],
            module_number=data['module_number'],
            lesson_number=data['lesson_number'],
            title=data['lesson_title'],
            description=data.get('lesson_description', ''),
            content=data.get('lesson_content', ''),
            video_url=video_url,
            order=(data['module_number'] * 100) + data['lesson_number']
        )
        
        db.add(lesson)
        db.commit()
        
        course = db.query(Course).filter(Course.id == data['course_id']).first()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="◀️ Назад к курсу",
                callback_data=f"manage_course_{data['course_id']}"
            )]
        ])
        
        await message.answer(
            f"✅ <b>Урок успешно добавлен!</b>\n\n"
            f"📖 Курс: {course.name}\n"
            f"📍 Модуль {data['module_number']}, Урок {data['lesson_number']}\n"
            f"📝 Название: {data['lesson_title']}",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("edit_lessons_"))
async def edit_lessons_list(callback: CallbackQuery):
    """Список уроков для редактирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
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
    """Меню редактирования урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    lesson_id = int(callback.data.split("_")[2])
    db: Session = get_db()
    
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            await callback.answer("Урок не найден", show_alert=True)
            return
        
        text = f"✏️ <b>Редактирование урока</b>\n\n"
        text += f"📍 Модуль {lesson.module_number}, Урок {lesson.lesson_number}\n"
        text += f"📝 Название: {lesson.title}\n"
        text += f"📄 Описание: {lesson.description[:100] if lesson.description else 'Не указано'}...\n"
        text += f"📖 Контент: {'Есть' if lesson.content else 'Нет'}\n"
        text += f"🎥 Видео: {'Есть' if lesson.video_url else 'Нет'}\n"
        
        buttons = [
            [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_title_{lesson_id}")],
            [InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"edit_desc_{lesson_id}")],
            [InlineKeyboardButton(text="✏️ Изменить контент", callback_data=f"edit_content_{lesson_id}")],
            [InlineKeyboardButton(text="✏️ Изменить видео", callback_data=f"edit_video_{lesson_id}")],
            [InlineKeyboardButton(text="🗑 Удалить урок", callback_data=f"delete_lesson_{lesson_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_lessons_{lesson.course_id}")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title_"))
async def edit_lesson_title_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия"""
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
            ('Курсов', db.query(Course).count()),
            ('Консультаций', db.query(Consultation).count()),
            ('Уроков', db.query(Lesson).count()),
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
            if payment.course_id:
                course = db.query(Course).filter(Course.id == payment.course_id).first()
                product_name = f"Курс: {course.name}" if course else "Курс"
            elif payment.consultation_id:
                consultation = db.query(Consultation).filter(Consultation.id == payment.consultation_id).first()
                product_name = f"Консультация: {consultation.name}" if consultation else "Консультация"
            
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
        
        # Лист 4: Курсы и их популярность
        ws_courses = wb.create_sheet("Курсы")
        
        headers = ['ID', 'Название', 'Уроков', 'Тарифов', 'Продаж', 'Выручка, ₽', 'Активен']
        for col, header in enumerate(headers, 1):
            cell = ws_courses.cell(1, col, header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        courses = db.query(Course).all()
        
        for row, course in enumerate(courses, 2):
            lessons_count = db.query(Lesson).filter(Lesson.course_id == course.id).count()
            tariffs_count = len(course.tariffs)
            
            sales_count = db.query(Payment).filter(
                Payment.course_id == course.id,
                Payment.status == 'succeeded'
            ).count()
            
            revenue = db.query(func.sum(Payment.amount)).filter(
                Payment.course_id == course.id,
                Payment.status == 'succeeded'
            ).scalar() or 0
            
            ws_courses.cell(row, 1, course.id)
            ws_courses.cell(row, 2, course.name)
            ws_courses.cell(row, 3, lessons_count)
            ws_courses.cell(row, 4, tariffs_count)
            ws_courses.cell(row, 5, sales_count)
            ws_courses.cell(row, 6, revenue)
            ws_courses.cell(row, 7, 'Да' if course.is_active else 'Нет')
        
        for col, width in zip(['A', 'B', 'C', 'D', 'E', 'F', 'G'], [8, 30, 10, 10, 10, 15, 10]):
            ws_courses.column_dimensions[col].width = width
        
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
                   "• Все покупки\n"
                   "• Аналитику по курсам"
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
    
    db: Session = get_db()
    
    try:
        consultations = db.query(Consultation).order_by(Consultation.order).all()
        
        if not consultations:
            await callback.message.edit_text(
                "🔮 <b>Консультации отсутствуют</b>\n\n"
                "Создайте консультации через utils/admin.py",
                reply_markup=get_back_to_admin_keyboard()
            )
        else:
            buttons = []
            for cons in consultations:
                status_emoji = "✅" if cons.is_active else "❌"
                price_text = f"{cons.price:,.0f} ₽" if cons.price else "Варианты"
                buttons.append([InlineKeyboardButton(
                    text=f"{cons.emoji} {cons.name} ({price_text}) {status_emoji}",
                    callback_data=f"manage_consultation_{cons.id}"
                )])
            
            buttons.append([InlineKeyboardButton(
                text="➕ Создать новую консультацию",
                callback_data="create_consultation"
            )])
            buttons.append([InlineKeyboardButton(
                text="◀️ Назад в админ-панель",
                callback_data="admin_panel"
            )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(
                "🔮 <b>Управление консультациями</b>\n\n"
                "Выберите консультацию для редактирования или создайте новую:",
                reply_markup=keyboard
            )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("manage_consultation_"))
async def manage_consultation(callback: CallbackQuery):
    """Управление конкретной консультацией"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    cons_id = int(callback.data.split("_")[2])
    db: Session = get_db()
    
    try:
        cons = db.query(Consultation).filter(Consultation.id == cons_id).first()
        
        if not cons:
            await callback.answer("Консультация не найдена", show_alert=True)
            return
        
        text = f"🔮 <b>{cons.name}</b>\n\n"
        text += f"📍 Slug: <code>{cons.slug}</code>\n"
        text += f"💰 Цена: {cons.price:,.0f} ₽\n" if cons.price else "💰 Цена: варианты\n"
        text += f"⏱ Длительность: {cons.duration}\n" if cons.duration else ""
        text += f"📂 Категория: {cons.category}\n"
        text += f"🔄 Порядок: {cons.order}\n"
        text += f"✅ Активна: {'Да' if cons.is_active else 'Нет'}\n"
        
        if cons.options:
            text += f"\n📋 Вариантов: {len(cons.options)}\n"
            for opt in cons.options:
                text += f"  • {opt.name}: {opt.price:,.0f} ₽\n"
        
        buttons = [
            [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_cons_name_{cons_id}")],
            [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"edit_cons_price_{cons_id}")],
            [InlineKeyboardButton(text="⏱ Изменить длительность", callback_data=f"edit_cons_duration_{cons_id}")],
            [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_cons_desc_{cons_id}")],
            [InlineKeyboardButton(
                text=f"{'❌ Деактивировать' if cons.is_active else '✅ Активировать'}",
                callback_data=f"toggle_cons_{cons_id}"
            )],
            [InlineKeyboardButton(text="◀️ Назад к консультациям", callback_data="admin_consultations")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_cons_"))
async def toggle_consultation(callback: CallbackQuery):
    """Переключить активность консультации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    cons_id = int(callback.data.split("_")[2])
    db: Session = get_db()
    
    try:
        cons = db.query(Consultation).filter(Consultation.id == cons_id).first()
        cons.is_active = not cons.is_active
        db.commit()
        
        await callback.answer(f"✅ Консультация {'активирована' if cons.is_active else 'деактивирована'}!")
        
        # Обновляем сообщение
        await manage_consultation(callback)
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("edit_cons_name_"))
async def edit_consultation_name_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия консультации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    cons_id = int(callback.data.split("_")[3])
    await state.update_data(editing_cons_id=cons_id)
    
    db: Session = get_db()
    try:
        cons = db.query(Consultation).filter(Consultation.id == cons_id).first()
        
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_consultation_{cons_id}")]
        ])
        
        await callback.message.edit_text(
            f"✏️ <b>Редактирование названия консультации</b>\n\n"
            f"Текущее название: <b>{cons.name}</b>\n\n"
            f"Отправьте новое название:",
            reply_markup=cancel_keyboard
        )
        
        await state.set_state(ConsultationManagement.editing_name)
    
    finally:
        db.close()
    
    await callback.answer()


@router.message(ConsultationManagement.editing_name)
async def edit_consultation_name_save(message: Message, state: FSMContext):
    """Сохранение нового названия консультации"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    cons_id = data['editing_cons_id']
    
    db: Session = get_db()
    try:
        cons = db.query(Consultation).filter(Consultation.id == cons_id).first()
        cons.name = message.text.strip()
        db.commit()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к консультации", callback_data=f"manage_consultation_{cons_id}")]
        ])
        
        await message.answer(
            f"✅ Название обновлено!\n\n"
            f"Новое название: <b>{cons.name}</b>",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("edit_cons_price_"))
async def edit_consultation_price_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования цены консультации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    cons_id = int(callback.data.split("_")[3])
    await state.update_data(editing_cons_id=cons_id)
    
    db: Session = get_db()
    try:
        cons = db.query(Consultation).filter(Consultation.id == cons_id).first()
        
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_consultation_{cons_id}")]
        ])
        
        current_price = f"{cons.price:,.0f} ₽" if cons.price else "Не указана"
        
        await callback.message.edit_text(
            f"💰 <b>Редактирование цены консультации</b>\n\n"
            f"Текущая цена: {current_price}\n\n"
            f"Отправьте новую цену (только число):",
            reply_markup=cancel_keyboard
        )
        
        await state.set_state(ConsultationManagement.editing_price)
    
    finally:
        db.close()
    
    await callback.answer()


@router.message(ConsultationManagement.editing_price)
async def edit_consultation_price_save(message: Message, state: FSMContext):
    """Сохранение новой цены консультации"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    cons_id = data['editing_cons_id']
    
    try:
        new_price = float(message.text.strip().replace(',', '.'))
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (например: 15000 или 15000.50)")
        return
    
    db: Session = get_db()
    try:
        cons = db.query(Consultation).filter(Consultation.id == cons_id).first()
        cons.price = new_price
        db.commit()
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к консультации", callback_data=f"manage_consultation_{cons_id}")]
        ])
        
        await message.answer(
            f"✅ Цена обновлена!\n\n"
            f"Новая цена: {new_price:,.0f} ₽",
            reply_markup=back_keyboard
        )
    
    finally:
        db.close()
        await state.clear()


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


@router.callback_query(F.data == "create_consultation")
async def create_consultation_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания новой консультации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_consultations")]
    ])
    
    await callback.message.edit_text(
        "➕ <b>Создание новой консультации</b>\n\n"
        "Шаг 1/6: Введите название консультации:",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(ConsultationManagement.creating_name)
    await callback.answer()


@router.message(ConsultationManagement.creating_name)
async def create_consultation_name(message: Message, state: FSMContext):
    """Получение названия консультации"""
    if not is_admin(message.from_user.id):
        return
    
    await state.update_data(cons_name=message.text.strip())
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_consultations")]
    ])
    
    await message.answer(
        f"✅ Название: <b>{message.text.strip()}</b>\n\n"
        f"Шаг 2/6: Введите slug (для URL, например: natal-chart):",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(ConsultationManagement.creating_slug)


@router.message(ConsultationManagement.creating_slug)
async def create_consultation_slug(message: Message, state: FSMContext):
    """Получение slug консультации"""
    if not is_admin(message.from_user.id):
        return
    
    slug = message.text.strip().lower().replace(' ', '-')
    
    # Проверяем уникальность
    db: Session = get_db()
    try:
        existing = db.query(Consultation).filter(Consultation.slug == slug).first()
        if existing:
            await message.answer("❌ Консультация с таким slug уже существует. Введите другой:")
            return
    finally:
        db.close()
    
    await state.update_data(cons_slug=slug)
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_consultations")]
    ])
    
    await message.answer(
        f"✅ Slug: <code>{slug}</code>\n\n"
        f"Шаг 3/6: Введите эмодзи (один символ, например: 🌟):",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(ConsultationManagement.creating_emoji)


@router.message(ConsultationManagement.creating_emoji)
async def create_consultation_emoji(message: Message, state: FSMContext):
    """Получение эмодзи консультации"""
    if not is_admin(message.from_user.id):
        return
    
    await state.update_data(cons_emoji=message.text.strip())
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_consultations")]
    ])
    
    await message.answer(
        f"✅ Эмодзи: {message.text.strip()}\n\n"
        f"Шаг 4/6: Введите цену (только число, например: 15000):",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(ConsultationManagement.creating_price)


@router.message(ConsultationManagement.creating_price)
async def create_consultation_price(message: Message, state: FSMContext):
    """Получение цены консультации"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        price = float(message.text.strip().replace(',', '.'))
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")
        return
    
    await state.update_data(cons_price=price)
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_consultations")]
    ])
    
    await message.answer(
        f"✅ Цена: {price:,.0f} ₽\n\n"
        f"Шаг 5/6: Введите длительность (например: 90 минут):",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(ConsultationManagement.creating_duration)


@router.message(ConsultationManagement.creating_duration)
async def create_consultation_duration(message: Message, state: FSMContext):
    """Получение длительности консультации"""
    if not is_admin(message.from_user.id):
        return
    
    await state.update_data(cons_duration=message.text.strip())
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_consultations")]
    ])
    
    await message.answer(
        f"✅ Длительность: {message.text.strip()}\n\n"
        f"Шаг 6/6: Введите описание консультации:",
        reply_markup=cancel_keyboard
    )
    
    await state.set_state(ConsultationManagement.creating_description)


@router.message(ConsultationManagement.creating_description)
async def create_consultation_save(message: Message, state: FSMContext):
    """Сохранение новой консультации"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    
    db: Session = get_db()
    try:
        # Получаем максимальный order
        max_order = db.query(func.max(Consultation.order)).scalar() or 0
        
        new_cons = Consultation(
            name=data['cons_name'],
            slug=data['cons_slug'],
            emoji=data['cons_emoji'],
            description=message.text.strip(),
            short_description=message.text.strip()[:200],
            price=data['cons_price'],
            duration=data['cons_duration'],
            is_active=True,
            order=max_order + 1,
            category='consultation'
        )
        
        db.add(new_cons)
        db.commit()
        db.refresh(new_cons)
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"manage_consultation_{new_cons.id}")],
            [InlineKeyboardButton(text="◀️ К списку консультаций", callback_data="admin_consultations")]
        ])
        
        await message.answer(
            f"✅ <b>Консультация успешно создана!</b>\n\n"
            f"{new_cons.emoji} {new_cons.name}\n"
            f"💰 {new_cons.price:,.0f} ₽\n"
            f"⏱ {new_cons.duration}\n"
            f"🔗 Slug: <code>{new_cons.slug}</code>",
            reply_markup=back_keyboard
        )
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании консультации: {str(e)}")
    
    finally:
        db.close()
        await state.clear()


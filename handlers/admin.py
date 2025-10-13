from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import config
from database import get_db, User, Payment, Course, Consultation, Lesson
from keyboards import get_admin_keyboard, get_back_to_admin_keyboard

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
        
        # Курсы и консультации
        total_courses = db.query(Course).count()
        total_consultations = db.query(Consultation).count()
        
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
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_to_admin_keyboard()
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def show_users(callback: CallbackQuery):
    """Показать последних пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        # Последние 10 пользователей
        users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
        
        users_text = "👥 <b>Последние пользователи:</b>\n\n"
        
        for user in users:
            username = f"@{user.username}" if user.username else "Без username"
            name = user.first_name or "Без имени"
            
            # Количество покупок
            purchases_count = len(user.payments)
            
            users_text += f"• {name} ({username})\n"
            users_text += f"  ID: <code>{user.telegram_id}</code>\n"
            users_text += f"  Покупок: {purchases_count}\n"
            users_text += f"  Регистрация: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        
        await callback.message.edit_text(
            users_text,
            reply_markup=get_back_to_admin_keyboard()
        )
    
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "admin_purchases")
async def show_purchases(callback: CallbackQuery):
    """Показать последние покупки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        # Последние 10 покупок
        purchases = db.query(Payment).order_by(Payment.created_at.desc()).limit(10).all()
        
        if not purchases:
            purchases_text = "📦 <b>Покупки отсутствуют</b>"
        else:
            purchases_text = "📦 <b>Последние покупки:</b>\n\n"
            
            for purchase in purchases:
                user = purchase.user
                username = f"@{user.username}" if user.username else "Без username"
                name = user.first_name or "Без имени"
                
                # Тип покупки
                item_type = "Курс" if purchase.course_id else "Консультация"
                item_name = ""
                if purchase.course_id:
                    course = db.query(Course).filter(Course.id == purchase.course_id).first()
                    item_name = course.name if course else "Неизвестно"
                elif purchase.consultation_id:
                    consultation = db.query(Consultation).filter(
                        Consultation.id == purchase.consultation_id
                    ).first()
                    item_name = consultation.name if consultation else "Неизвестно"
                
                purchases_text += f"• {name} ({username})\n"
                purchases_text += f"  {item_type}: {item_name}\n"
                purchases_text += f"  Сумма: {purchase.amount:,.0f} ₽\n"
                purchases_text += f"  Дата: {purchase.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        await callback.message.edit_text(
            purchases_text,
            reply_markup=get_back_to_admin_keyboard()
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
                text="◀️ Назад в админ-панель",
                callback_data="admin_panel"
            )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(
                "📚 <b>Управление курсами</b>\n\n"
                "Выберите курс для редактирования:",
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


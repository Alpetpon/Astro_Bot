"""
Хэндлеры для учебного бота - доступ к материалам купленных курсов
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_db, UserRepository, PaymentRepository
from data import (
    get_course_by_slug,
    get_course_modules,
    get_module_by_id,
    get_lesson_by_id,
    get_mini_course
)

logger = logging.getLogger(__name__)
learning_router = Router()


@learning_router.message(Command("start"))
async def cmd_start(message: Message):
    """Стартовое сообщение учебного бота"""
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    # Создаем или обновляем пользователя
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    
    if not user:
        from database import User
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        user = await user_repo.create(user)
        logger.info(f"New user created in learning bot: {user.telegram_id}")
    else:
        await user_repo.update_activity(message.from_user.id)
    
    # Проверяем купленные курсы
    payments = await payment_repo.get_user_payments(user.id)
    purchased_courses = [p for p in payments if p.status == 'succeeded' and p.product_type in ['course', 'mini_course']]
    
    if not purchased_courses:
        text = "🎓 <b>Учебный бот</b>\n\n"
        text += "У вас пока нет доступных курсов для обучения.\n\n"
        text += "Чтобы получить доступ к курсам, приобретите их в основном боте."
        
        await message.answer(text)
        return
    
    # Показываем список доступных курсов
    text = "🎓 <b>Добро пожаловать в учебный бот!</b>\n\n"
    text += "📚 Здесь вы можете изучать купленные курсы и материалы.\n\n"
    text += f"<b>Доступных курсов:</b> {len(purchased_courses)}\n\n"
    text += "Выберите курс для начала обучения:"
    
    buttons = []
    
    # Добавляем кнопки для каждого купленного курса
    for payment in purchased_courses:
        if payment.course_slug == "mini_course":
            mini_course = get_mini_course()
            if mini_course:
                course_name = mini_course.get('title', 'Мини-курс')
                emoji = mini_course.get('emoji', '🌌')
                buttons.append([InlineKeyboardButton(
                    text=f"{emoji} {course_name}",
                    callback_data=f"my_course_{payment.course_slug}"
                )])
        else:
            course = get_course_by_slug(payment.course_slug)
            if course:
                course_name = course.get('name', payment.course_slug)
                emoji = course.get('emoji', '📚')
                buttons.append([InlineKeyboardButton(
                    text=f"{emoji} {course_name}",
                    callback_data=f"my_course_{payment.course_slug}"
                )])
    
    # Кнопка "Мои курсы" (главное меню)
    buttons.append([InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(text, reply_markup=keyboard)


@learning_router.callback_query(F.data == "my_courses")
async def show_my_courses(callback: CallbackQuery):
    """Показать список купленных курсов"""
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if user:
            await user_repo.update_activity(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        # Получаем купленные курсы
        payments = await payment_repo.get_user_payments(user.id)
        purchased_courses = [p for p in payments if p.status == 'succeeded' and p.product_type in ['course', 'mini_course']]
        
        if not purchased_courses:
            text = "📚 У вас пока нет купленных курсов.\n\n"
            text += "Приобретите курсы в основном боте для начала обучения."
            
            await callback.message.edit_text(text)
            await callback.answer()
            return
        
        # Формируем список курсов
        text = "📚 <b>Мои курсы</b>\n\n"
        text += f"Всего курсов: {len(purchased_courses)}\n\n"
        
        buttons = []
        
        for payment in purchased_courses:
            if payment.course_slug == "mini_course":
                mini_course = get_mini_course()
                if mini_course:
                    course_name = mini_course.get('title', 'Мини-курс')
                    emoji = mini_course.get('emoji', '🌌')
                    
                    paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                    text += f"{emoji} <b>{course_name}</b>\n"
                    text += f"Дата покупки: {paid_date}\n\n"
                    
                    buttons.append([InlineKeyboardButton(
                        text=f"{emoji} {course_name}",
                        callback_data=f"my_course_{payment.course_slug}"
                    )])
            else:
                course = get_course_by_slug(payment.course_slug)
                if course:
                    course_name = course.get('name', payment.course_slug)
                    emoji = course.get('emoji', '📚')
                    
                    paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                    text += f"{emoji} <b>{course_name}</b>\n"
                    text += f"Дата покупки: {paid_date}\n\n"
                    
                    buttons.append([InlineKeyboardButton(
                        text=f"{emoji} {course_name}",
                        callback_data=f"my_course_{payment.course_slug}"
                    )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_my_courses: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@learning_router.callback_query(F.data.startswith("my_course_"))
async def show_my_course(callback: CallbackQuery):
    """Показать купленный курс с материалами"""
    course_slug = callback.data.replace("my_course_", "")
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        # Проверяем, что пользователь купил этот курс
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        # Проверяем наличие успешного платежа за курс
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        # Получаем информацию о курсе
        if course_slug == "mini_course":
            mini_course = get_mini_course()
            
            if not mini_course:
                await callback.answer("Мини-курс не найден", show_alert=True)
                return
            
            # Формируем текст с материалами мини-курса
            emoji = mini_course.get('emoji', '🌌')
            text = f"{emoji} <b>{mini_course.get('title', 'Мини-курс')}</b>\n\n"
            
            subtitle = mini_course.get('subtitle', '')
            if subtitle:
                text += f"<i>{subtitle}</i>\n\n"
            
            if payment.paid_at:
                paid_date = payment.paid_at.strftime('%d.%m.%Y')
                text += f"💳 <b>Дата покупки:</b> {paid_date}\n"
            
            text += "\n✅ <b>У вас есть доступ к материалам мини-курса</b>\n\n"
            
            modules = mini_course.get('modules', [])
            
            if modules:
                # Вычисляем количество полных суток с момента покупки
                if payment.paid_at:
                    time_since_purchase = datetime.utcnow() - payment.paid_at
                    days_passed = int(time_since_purchase.total_seconds() / 86400)
                else:
                    days_passed = 0
                
                text += "📚 <b>Модули курса:</b>\n\n"
                
                buttons = []
                
                for module in modules:
                    day_number = module.get('day_number', 999)
                    module_title = module.get('title', 'Модуль')
                    module_emoji = module.get('emoji', '📖')
                    
                    is_available = days_passed >= (day_number - 1)
                    
                    if is_available:
                        text += f"✅ {module_emoji} {module_title}\n"
                        buttons.append([InlineKeyboardButton(
                            text=f"{module_emoji} {module_title}",
                            callback_data=f"mini_module_{module['id']}"
                        )])
                    else:
                        days_until_unlock = (day_number - 1) - days_passed
                        unlock_date = payment.paid_at + timedelta(days=(day_number - 1))
                        unlock_date_str = unlock_date.strftime('%d.%m.%Y %H:%M')
                        
                        time_until_unlock = unlock_date - datetime.utcnow()
                        hours_until_unlock = int(time_until_unlock.total_seconds() / 3600)
                        
                        if hours_until_unlock < 24:
                            time_str = f"через {hours_until_unlock} ч."
                        else:
                            time_str = f"через {days_until_unlock} дн."
                        
                        text += f"🔒 {module_emoji} {module_title}\n"
                        text += f"   Откроется: {unlock_date_str} ({time_str})\n"
                
                text += "\n💡 Новый модуль открывается каждый день!"
                
                buttons.append([InlineKeyboardButton(text="◀️ Мои курсы", callback_data="my_courses")])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            else:
                text += "🔧 <i>Материалы мини-курса скоро будут доступны.</i>"
                
                buttons = [[InlineKeyboardButton(text="◀️ Мои курсы", callback_data="my_courses")]]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        # Обычный курс
        course = get_course_by_slug(course_slug)
        
        if not course:
            await callback.answer("Курс не найден", show_alert=True)
            return
        
        # Формируем текст с материалами курса
        emoji = course.get('emoji', '📚')
        text = f"{emoji} <b>{course['name']}</b>\n\n"
        
        duration = course.get('duration', 'не указана')
        text += f"⏱ <b>Длительность:</b> {duration}\n"
        
        if payment.paid_at:
            paid_date = payment.paid_at.strftime('%d.%m.%Y')
            text += f"📅 <b>Дата покупки:</b> {paid_date}\n"
        
        text += "\n✅ <b>У вас есть доступ к материалам курса</b>\n\n"
        
        modules = get_course_modules(course_slug)
        
        if modules:
            text += "📚 <b>Модули курса:</b>\n\n"
            
            buttons = []
            
            for module in modules:
                module_title = module.get('title', 'Модуль')
                text += f"▫️ {module_title}\n\n"
                
                buttons.append([InlineKeyboardButton(
                    text=f"📚 {module_title}",
                    callback_data=f"module_{course_slug}_{module['id']}"
                )])
            
            text += "\n💡 Выберите модуль, чтобы начать обучение!"
        else:
            text += "🔧 <i>Материалы курса скоро будут доступны.</i>\n\n"
            
            buttons = []
        
        buttons.append([InlineKeyboardButton(text="◀️ Мои курсы", callback_data="my_courses")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_my_course: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке курса", show_alert=True)


@learning_router.callback_query(F.data.startswith("module_"))
async def show_module(callback: CallbackQuery):
    """Показать модуль курса с уроками"""
    parts = callback.data.split("_", 2)
    if len(parts) < 3:
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    
    course_slug = parts[1]
    module_id = parts[2]
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        module = get_module_by_id(course_slug, module_id)
        
        if not module:
            await callback.answer("Модуль не найден", show_alert=True)
            return
        
        course = get_course_by_slug(course_slug)
        
        emoji = course.get('emoji', '📚') if course else '📚'
        text = f"{emoji} <b>{module['title']}</b>\n\n"
        
        description = module.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        lessons = module.get('lessons', [])
        
        if lessons:
            text += "📖 <b>Уроки модуля:</b>\n\n"
            
            buttons = []
            
            for i, lesson in enumerate(lessons, 1):
                lesson_title = lesson.get('title', f'Урок {i}')
                lesson_type = lesson.get('type', 'video')
                
                type_emoji = {
                    'video': '🎥',
                    'homework': '📝',
                    'test': '✅',
                    'material': '📄'
                }.get(lesson_type, '📖')
                
                text += f"{i}. {type_emoji} {lesson_title}\n"
                
                buttons.append([InlineKeyboardButton(
                    text=f"{type_emoji} Урок {i}: {lesson_title[:30]}{'...' if len(lesson_title) > 30 else ''}",
                    callback_data=f"lesson_{course_slug}_{module_id}_{lesson['id']}"
                )])
            
            text += "\n💡 Нажмите на урок, чтобы начать изучение!"
            
            buttons.append([
                InlineKeyboardButton(text="◀️ К курсу", callback_data=f"my_course_{course_slug}"),
                InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        else:
            text += "📚 Уроки скоро будут добавлены."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К курсу", callback_data=f"my_course_{course_slug}")]
            ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_module: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке модуля", show_alert=True)


@learning_router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    """Показать урок"""
    parts = callback.data.split("_", 3)
    if len(parts) < 4:
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    
    course_slug = parts[1]
    module_id = parts[2]
    lesson_id = parts[3]
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
        
        if not lesson:
            await callback.answer("Урок не найден", show_alert=True)
            return
        
        lesson_type = lesson.get('type', 'video')
        type_emoji = {
            'video': '🎥',
            'homework': '📝',
            'test': '✅',
            'material': '📄'
        }.get(lesson_type, '📖')
        
        text = f"{type_emoji} <b>{lesson['title']}</b>\n\n"
        
        description = lesson.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        has_content = False
        
        video_url = lesson.get('video_url', '')
        if video_url:
            text += "🎬 <b>Видео урока доступно для просмотра</b>\n\n"
            has_content = True
        
        lecture_file_id = lesson.get('lecture_file_id', '')
        if lecture_file_id:
            text += "📄 <b>Лекция доступна для скачивания</b>\n\n"
            has_content = True
        
        text_content = lesson.get('text_content', '')
        if text_content:
            text += f"📝 <b>Содержание урока:</b>\n{text_content}\n\n"
            has_content = True
        
        if not has_content:
            if lesson_type == 'homework':
                text += "✍️ Это домашнее задание для самостоятельной работы.\n\n"
            else:
                text += "🔧 Материалы урока скоро будут добавлены.\n\n"
        
        materials = lesson.get('materials', [])
        if materials:
            text += "📎 <b>Дополнительные материалы:</b>\n"
            for material in materials:
                material_title = material.get('title', 'Материал')
                material_file_id = material.get('file_id', '')
                
                if material_file_id:
                    text += f"▫️ {material_title}\n"
                    try:
                        await callback.message.answer_document(
                            document=material_file_id,
                            caption=material_title
                        )
                    except Exception as e:
                        logger.error(f"Error sending material: {e}")
                else:
                    text += f"▫️ {material_title} (скоро будет доступен)\n"
            text += "\n"
        
        buttons = []
        
        if video_url:
            buttons.append([InlineKeyboardButton(text="🎬 Смотреть видео", url=video_url)])
        
        if lecture_file_id:
            buttons.append([InlineKeyboardButton(text="📄 Скачать лекцию", callback_data=f"download_lecture_{course_slug}_{module_id}_{lesson_id}")])
        
        buttons.extend([
            [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"module_{course_slug}_{module_id}")],
            [
                InlineKeyboardButton(text="📚 К курсу", callback_data=f"my_course_{course_slug}"),
                InlineKeyboardButton(text="🏠 Мои курсы", callback_data="my_courses")
            ]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_lesson: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке урока", show_alert=True)


@learning_router.callback_query(F.data.startswith("download_lecture_"))
async def download_lecture(callback: CallbackQuery):
    """Скачать PDF лекцию урока"""
    parts = callback.data.replace("download_lecture_", "").split("_", 2)
    
    if len(parts) < 3:
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    
    course_slug = parts[0]
    module_id = parts[1]
    lesson_id = parts[2]
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
        
        if not lesson:
            await callback.answer("Урок не найден", show_alert=True)
            return
        
        lecture_file_id = lesson.get('lecture_file_id', '')
        
        if not lecture_file_id:
            await callback.answer("Лекция недоступна", show_alert=True)
            return
        
        try:
            await callback.message.answer_document(
                document=lecture_file_id,
                caption=f"📄 Лекция: {lesson['title']}"
            )
            await callback.answer("✅ Лекция отправлена")
        except Exception as e:
            logger.error(f"Error sending lecture file: {e}")
            await callback.answer("❌ Ошибка при загрузке лекции", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in download_lecture: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@learning_router.callback_query(F.data.startswith("mini_module_"))
async def show_mini_module(callback: CallbackQuery):
    """Показать модуль мини-курса с уроками"""
    module_id = callback.data.replace("mini_module_", "")
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == "mini_course" and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к мини-курсу", show_alert=True)
            return
        
        mini_course = get_mini_course()
        
        if not mini_course:
            await callback.answer("Мини-курс не найден", show_alert=True)
            return
        
        modules = mini_course.get('modules', [])
        module = next((m for m in modules if m['id'] == module_id), None)
        
        if not module:
            await callback.answer("Модуль не найден", show_alert=True)
            return
        
        # Проверяем доступ к модулю
        day_number = module.get('day_number', 999)
        if payment.paid_at:
            time_since_purchase = datetime.utcnow() - payment.paid_at
            days_passed = int(time_since_purchase.total_seconds() / 86400)
        else:
            days_passed = 0
        
        is_available = days_passed >= (day_number - 1)
        
        if not is_available:
            await callback.answer("Этот модуль пока недоступен", show_alert=True)
            return
        
        emoji = module.get('emoji', '📖')
        text = f"{emoji} <b>{module['title']}</b>\n\n"
        
        description = module.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        lessons = module.get('lessons', [])
        
        if lessons:
            text += "📖 <b>Уроки:</b>\n\n"
            
            buttons = []
            
            for i, lesson in enumerate(lessons, 1):
                lesson_title = lesson.get('title', f'Урок {i}')
                lesson_type = lesson.get('type', 'video')
                
                type_emoji = {
                    'video': '🎥',
                    'homework': '📝',
                    'test': '✅',
                    'material': '📄'
                }.get(lesson_type, '📖')
                
                text += f"{i}. {type_emoji} {lesson_title}\n"
                
                buttons.append([InlineKeyboardButton(
                    text=f"{type_emoji} Урок {i}: {lesson_title[:30]}{'...' if len(lesson_title) > 30 else ''}",
                    callback_data=f"mini_lesson_{module_id}_{lesson['id']}"
                )])
            
            text += "\n💡 Нажмите на урок, чтобы начать!"
            
            buttons.append([
                InlineKeyboardButton(text="◀️ К мини-курсу", callback_data="my_course_mini_course"),
                InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        else:
            text += "📚 Уроки скоро будут добавлены."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К мини-курсу", callback_data="my_course_mini_course")]
            ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_mini_module: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке модуля", show_alert=True)


@learning_router.callback_query(F.data.startswith("mini_lesson_"))
async def show_mini_lesson(callback: CallbackQuery):
    """Показать урок мини-курса"""
    parts = callback.data.replace("mini_lesson_", "").split("_", 1)
    if len(parts) < 2:
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    
    module_id = parts[0]
    lesson_id = parts[1]
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == "mini_course" and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к мини-курсу", show_alert=True)
            return
        
        mini_course = get_mini_course()
        
        if not mini_course:
            await callback.answer("Мини-курс не найден", show_alert=True)
            return
        
        modules = mini_course.get('modules', [])
        module = next((m for m in modules if m['id'] == module_id), None)
        
        if not module:
            await callback.answer("Модуль не найден", show_alert=True)
            return
        
        lessons = module.get('lessons', [])
        lesson = next((l for l in lessons if l['id'] == lesson_id), None)
        
        if not lesson:
            await callback.answer("Урок не найден", show_alert=True)
            return
        
        # Проверяем доступ к модулю
        day_number = module.get('day_number', 999)
        if payment.paid_at:
            time_since_purchase = datetime.utcnow() - payment.paid_at
            days_passed = int(time_since_purchase.total_seconds() / 86400)
        else:
            days_passed = 0
        
        is_available = days_passed >= (day_number - 1)
        
        if not is_available:
            await callback.answer("Этот урок пока недоступен", show_alert=True)
            return
        
        lesson_type = lesson.get('type', 'video')
        type_emoji = {
            'video': '🎥',
            'homework': '📝',
            'test': '✅',
            'material': '📄'
        }.get(lesson_type, '📖')
        
        text = f"{type_emoji} <b>{lesson['title']}</b>\n\n"
        
        description = lesson.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        has_content = False
        
        video_url = lesson.get('video_url', '')
        if video_url:
            text += f"🎬 <a href='{video_url}'>Смотреть видео</a>\n\n"
            has_content = True
        
        text_content = lesson.get('text_content', '')
        if text_content:
            text += f"📝 <b>Содержание урока:</b>\n{text_content}\n\n"
            has_content = True
        
        if not has_content:
            if lesson_type == 'homework':
                text += "✍️ Это домашнее задание для самостоятельной работы.\n\n"
            else:
                text += "🔧 Материалы урока скоро будут добавлены.\n\n"
        
        buttons = [
            [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"mini_module_{module_id}")],
            [
                InlineKeyboardButton(text="📚 К мини-курсу", callback_data="my_course_mini_course"),
                InlineKeyboardButton(text="🏠 Мои курсы", callback_data="my_courses")
            ]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_mini_lesson: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке урока", show_alert=True)


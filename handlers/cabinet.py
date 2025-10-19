import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bson import ObjectId

from database import get_db, UserRepository, PaymentRepository
from keyboards import get_back_keyboard
from data import (
    get_course_by_slug, 
    get_consultation_by_slug,
    get_course_modules,
    get_module_by_id,
    get_lesson_by_id
)

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_cabinet")
async def show_my_cabinet(callback: CallbackQuery):
    """Показать личный кабинет"""
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        # Обновляем активность
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if user:
            await user_repo.update_activity(callback.from_user.id)
        
        # Проверяем платежи
        payments = await payment_repo.get_user_payments(user.id)
        # Фильтруем только успешные платежи
        payments = [p for p in payments if p.status == 'succeeded']
        
        # Считаем статистику
        courses_count = len([p for p in payments if p.product_type in ['course', 'mini_course']])
        consultations_count = len([p for p in payments if p.product_type == 'consultation'])
        guides_count = len([p for p in payments if p.product_type == 'guide'])
        total_spent = sum(p.amount for p in payments)
        
        # Формируем текст
        text = "<b>Мой кабинет</b>\n\n"
        
        text += "<b>Моя статистика:</b>\n"
        text += f"• Курсов: {courses_count}\n"
        text += f"• Консультаций: {consultations_count}\n"
        text += f"• Гайдов: {guides_count}\n\n"
        text += f"Всего потрачено: {total_spent:,.0f} ₽\n\n"
        
        # Создаём клавиатуру
        buttons = []
        
        if payments:
            text += "<b>Мои покупки:</b>\n\n"
            
            # Группируем покупки по типу
            courses = [p for p in payments if p.product_type in ['course', 'mini_course']]
            consultations = [p for p in payments if p.product_type == 'consultation']
            
            if courses:
                text += "<b>Курсы:</b>\n"
                for payment in courses:
                    # Проверяем, это мини-курс или обычный курс
                    if payment.course_slug == "mini_course":
                        from data import get_mini_course
                        mini_course = get_mini_course()
                        if mini_course:
                            course_name = mini_course.get('title', 'Мини-курс')
                            emoji = mini_course.get('emoji', '🌌')
                            text += f"• {emoji} {course_name}\n"
                            # Добавляем кнопку для перехода к купленному мини-курсу
                            buttons.append([InlineKeyboardButton(
                                text=f"{emoji} {course_name}",
                                callback_data=f"my_course_{payment.course_slug}"
                            )])
                    else:
                        course = get_course_by_slug(payment.course_slug)
                        if course:
                            course_name = course.get('name', payment.course_slug)
                            emoji = course.get('emoji', '📚')
                            text += f"• {emoji} {course_name}\n"
                            # Добавляем кнопку для перехода к купленному курсу с материалами
                            buttons.append([InlineKeyboardButton(
                                text=f"{emoji} {course_name}",
                                callback_data=f"my_course_{payment.course_slug}"
                            )])
                text += "\n"
            
            if consultations:
                text += "\n<b>Консультации:</b>\n"
                for payment in consultations:
                    consultation = get_consultation_by_slug(payment.consultation_slug)
                    if consultation:
                        consultation_name = consultation.get('name', payment.consultation_slug)
                        emoji = consultation.get('emoji', '🔮')
                        text += f"• {emoji} {consultation_name}\n"
                        paid_date = payment.paid_at.strftime('%d.%m.%Y') if payment.paid_at else "недавно"
                        text += f"  Оплачено: {paid_date}\n"
                text += "\n"
        else:
            text += "📚 У вас пока нет купленных курсов или консультаций.\n\n"
            text += "Перейдите в каталог, чтобы выбрать подходящий курс!"
            
            # Добавляем кнопки для перехода к каталогам
            buttons.append([InlineKeyboardButton(text="📚 Каталог курсов", callback_data="courses")])
            buttons.append([InlineKeyboardButton(text="🔮 Консультации", callback_data="consultations")])
            buttons.append([InlineKeyboardButton(text="💕 Гайды", callback_data="guides_list")])
        
        # Кнопка назад
        buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_my_cabinet: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "my_courses")
async def show_my_courses(callback: CallbackQuery):
    """Перенаправление на личный кабинет (для совместимости)"""
    # Перенаправляем на my_cabinet
    await show_my_cabinet(callback)


@router.callback_query(F.data.startswith("my_course_"))
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
            from data import get_mini_course
            from datetime import datetime, timedelta
            
            mini_course = get_mini_course()
            
            if not mini_course:
                await callback.answer("Мини-курс не найден", show_alert=True)
                return
            
            # Формируем текст с материалами мини-курса
            emoji = mini_course.get('emoji', '🌌')
            text = f"{emoji} <b>{mini_course.get('title', 'Мини-курс')}</b>\n\n"
            
            # Информация о мини-курсе
            subtitle = mini_course.get('subtitle', '')
            if subtitle:
                text += f"<i>{subtitle}</i>\n\n"
            
            # Дата покупки
            if payment.paid_at:
                paid_date = payment.paid_at.strftime('%d.%m.%Y')
                text += f"💳 <b>Дата покупки:</b> {paid_date}\n"
            
            text += "\n✅ <b>У вас есть доступ к материалам мини-курса</b>\n\n"
            
            # Получаем модули
            modules = mini_course.get('modules', [])
            
            if modules:
                # Вычисляем количество полных суток (24 часа) с момента покупки
                if payment.paid_at:
                    time_since_purchase = datetime.utcnow() - payment.paid_at
                    days_passed = int(time_since_purchase.total_seconds() / 86400)  # 86400 секунд = 24 часа
                else:
                    days_passed = 0
                
                text += "📚 <b>Модули курса:</b>\n\n"
                
                # Клавиатура
                buttons = []
                
                # Проходим по всем модулям
                for module in modules:
                    day_number = module.get('day_number', 999)
                    module_title = module.get('title', 'Модуль')
                    module_emoji = module.get('emoji', '📖')
                    
                    # Модуль доступен, если прошло достаточно дней
                    # День 1 доступен сразу (day_number=1, days_passed>=0)
                    is_available = days_passed >= (day_number - 1)
                    
                    if is_available:
                        # Доступный модуль
                        text += f"✅ {module_emoji} {module_title}\n"
                        
                        # Добавляем кнопку для перехода к модулю
                        buttons.append([InlineKeyboardButton(
                            text=f"{module_emoji} {module_title}",
                            callback_data=f"mini_module_{module['id']}"
                        )])
                    else:
                        # Заблокированный модуль
                        days_until_unlock = (day_number - 1) - days_passed
                        unlock_date = payment.paid_at + timedelta(days=(day_number - 1))
                        unlock_date_str = unlock_date.strftime('%d.%m.%Y %H:%M')
                        
                        # Вычисляем оставшиеся часы
                        time_until_unlock = unlock_date - datetime.utcnow()
                        hours_until_unlock = int(time_until_unlock.total_seconds() / 3600)
                        
                        if hours_until_unlock < 24:
                            time_str = f"через {hours_until_unlock} ч."
                        else:
                            time_str = f"через {days_until_unlock} дн."
                        
                        text += f"🔒 {module_emoji} {module_title}\n"
                        text += f"   Откроется: {unlock_date_str} ({time_str})\n"
                
                text += "\n💡 Новый модуль открывается каждый день!"
                
                # Кнопки навигации
                buttons.append([
                    InlineKeyboardButton(text="◀️ Мой кабинет", callback_data="my_cabinet"),
                    InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
                ])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            else:
                # Если модулей нет
                text += "🔧 <i>Материалы мини-курса скоро будут доступны.</i>"
                
                # Клавиатура
                buttons = [[
                    InlineKeyboardButton(text="◀️ Мой кабинет", callback_data="my_cabinet"),
                    InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
                ]]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
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
        
        # Информация о курсе
        duration = course.get('duration', 'не указана')
        text += f"⏱ <b>Длительность:</b> {duration}\n"
        
        # Дата покупки
        if payment.paid_at:
            paid_date = payment.paid_at.strftime('%d.%m.%Y')
            text += f"📅 <b>Дата покупки:</b> {paid_date}\n"
        
        text += "\n"
        
        # Получаем модули курса
        modules = get_course_modules(course_slug)
        
        # Информация о доступе
        text += "✅ <b>У вас есть доступ к материалам курса</b>\n\n"
        
        if modules:
            text += "📚 <b>Модули курса:</b>\n\n"
            
            # Клавиатура
            buttons = []
            
            # Добавляем кнопки для каждого модуля
            for module in modules:
                module_title = module.get('title', 'Модуль')
                
                # Краткое название модуля для текста
                text += f"▫️ {module_title}\n\n"
                
                # Кнопка для перехода к модулю
                buttons.append([InlineKeyboardButton(
                    text=f"📚 {module_title}",
                    callback_data=f"module_{course_slug}_{module['id']}"
                )])
            
            text += "\n💡 Выберите модуль, чтобы начать обучение!"
        else:
            # Если материалов нет
            text += "🔧 <i>Материалы курса скоро будут доступны.\n"
            text += "Сейчас идет подготовка платформы для обучения.</i>\n\n"
            text += "📞 Если у вас возникли вопросы, свяжитесь с поддержкой."
            
            # Клавиатура
            buttons = []
            
            # Кнопка для связи с поддержкой
            from config import config
            if config.CONSULTATION_TELEGRAM:
                buttons.append([InlineKeyboardButton(
                    text="💬 Написать поддержке",
                    url=f"https://t.me/{config.CONSULTATION_TELEGRAM}"
                )])
        
        # Кнопки навигации
        buttons.append([
            InlineKeyboardButton(text="◀️ Мой кабинет", callback_data="my_cabinet"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_my_course: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке курса", show_alert=True)


@router.callback_query(F.data.startswith("module_"))
async def show_module(callback: CallbackQuery):
    """Показать модуль курса с уроками"""
    # Формат: module_{course_slug}_{module_id}
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
        # Проверяем доступ к курсу
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        # Получаем модуль
        module = get_module_by_id(course_slug, module_id)
        
        if not module:
            await callback.answer("Модуль не найден", show_alert=True)
            return
        
        # Получаем информацию о курсе
        course = get_course_by_slug(course_slug)
        
        # Формируем текст
        emoji = course.get('emoji', '📚') if course else '📚'
        text = f"{emoji} <b>{module['title']}</b>\n\n"
        
        description = module.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        # Список уроков
        lessons = module.get('lessons', [])
        
        if lessons:
            text += "📖 <b>Уроки модуля:</b>\n\n"
            
            buttons = []
            
            for i, lesson in enumerate(lessons, 1):
                lesson_title = lesson.get('title', f'Урок {i}')
                lesson_type = lesson.get('type', 'video')
                
                # Эмодзи в зависимости от типа урока
                type_emoji = {
                    'video': '🎥',
                    'homework': '📝',
                    'test': '✅',
                    'material': '📄'
                }.get(lesson_type, '📖')
                
                # Текст урока
                text += f"{i}. {type_emoji} {lesson_title}\n"
                
                # Кнопка для урока
                buttons.append([InlineKeyboardButton(
                    text=f"{type_emoji} Урок {i}: {lesson_title[:30]}{'...' if len(lesson_title) > 30 else ''}",
                    callback_data=f"lesson_{course_slug}_{module_id}_{lesson['id']}"
                )])
            
            text += "\n💡 Нажмите на урок, чтобы начать изучение!"
            
            # Кнопки навигации
            buttons.append([
                InlineKeyboardButton(text="◀️ К курсу", callback_data=f"my_course_{course_slug}"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        else:
            text += "📚 Уроки скоро будут добавлены."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К курсу", callback_data=f"my_course_{course_slug}")]
            ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_module: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке модуля", show_alert=True)


@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    """Показать урок"""
    # Формат: lesson_{course_slug}_{module_id}_{lesson_id}
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
        # Проверяем доступ к курсу
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        # Получаем урок
        lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
        
        if not lesson:
            await callback.answer("Урок не найден", show_alert=True)
            return
        
        # Формируем текст
        lesson_type = lesson.get('type', 'video')
        type_emoji = {
            'video': '🎥',
            'homework': '📝',
            'test': '✅',
            'material': '📄'
        }.get(lesson_type, '📖')
        
        text = f"{type_emoji} <b>{lesson['title']}</b>\n\n"
        
        # Описание урока
        description = lesson.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        # Отображение контента урока
        has_content = False
        
        # 1. Видео - теперь через кнопку
        video_url = lesson.get('video_url', '')
        if video_url:
            text += "🎬 <b>Видео урока доступно для просмотра</b>\n\n"
            has_content = True
        
        # 2. Лекция (PDF файл) - через кнопку
        lecture_file_id = lesson.get('lecture_file_id', '')
        if lecture_file_id:
            text += "📄 <b>Лекция доступна для скачивания</b>\n\n"
            has_content = True
        
        # 3. Текстовое содержание
        text_content = lesson.get('text_content', '')
        if text_content:
            text += f"📝 <b>Содержание урока:</b>\n{text_content}\n\n"
            has_content = True
        
        # Если нет контента
        if not has_content:
            if lesson_type == 'homework':
                text += "✍️ Это домашнее задание для самостоятельной работы.\n\n"
            else:
                text += "🔧 Материалы урока скоро будут добавлены.\n\n"
        
        # Дополнительные материалы
        materials = lesson.get('materials', [])
        if materials:
            text += "📎 <b>Дополнительные материалы:</b>\n"
            for material in materials:
                material_title = material.get('title', 'Материал')
                material_file_id = material.get('file_id', '')
                
                if material_file_id:
                    text += f"▫️ {material_title}\n"
                    # Отправим материал отдельно
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
        
        # Кнопки навигации
        buttons = []
        
        # Кнопка смотреть видео (если есть)
        if video_url:
            buttons.append([InlineKeyboardButton(text="🎬 Смотреть видео", url=video_url)])
        
        # Кнопка скачать лекцию (если есть)
        if lecture_file_id:
            buttons.append([InlineKeyboardButton(text="📄 Скачать лекцию", callback_data=f"download_lecture_{course_slug}_{module_id}_{lesson_id}")])
        
        buttons.extend([
            [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"module_{course_slug}_{module_id}")],
            [
                InlineKeyboardButton(text="📚 К курсу", callback_data=f"my_course_{course_slug}"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
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


@router.callback_query(F.data.startswith("download_lecture_"))
async def download_lecture(callback: CallbackQuery):
    """Скачать PDF лекцию урока"""
    # Формат: download_lecture_{course_slug}_{module_id}_{lesson_id}
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
        # Проверяем доступ к курсу
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        # Получаем урок
        lesson = get_lesson_by_id(course_slug, module_id, lesson_id)
        
        if not lesson:
            await callback.answer("Урок не найден", show_alert=True)
            return
        
        lecture_file_id = lesson.get('lecture_file_id', '')
        
        if not lecture_file_id:
            await callback.answer("Лекция недоступна", show_alert=True)
            return
        
        # Отправляем файл
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


@router.callback_query(F.data.startswith("mini_module_"))
async def show_mini_module(callback: CallbackQuery):
    """Показать модуль мини-курса с уроками"""
    module_id = callback.data.replace("mini_module_", "")
    
    db = await get_db()
    user_repo = UserRepository(db)
    payment_repo = PaymentRepository(db)
    
    try:
        # Проверяем доступ к мини-курсу
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == "mini_course" and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к мини-курсу", show_alert=True)
            return
        
        # Получаем мини-курс и модуль
        from data import get_mini_course
        from datetime import datetime
        
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
            days_passed = int(time_since_purchase.total_seconds() / 86400)  # 86400 секунд = 24 часа
        else:
            days_passed = 0
        
        is_available = days_passed >= (day_number - 1)
        
        if not is_available:
            await callback.answer("Этот модуль пока недоступен", show_alert=True)
            return
        
        # Формируем текст модуля
        emoji = module.get('emoji', '📖')
        text = f"{emoji} <b>{module['title']}</b>\n\n"
        
        description = module.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        # Список уроков
        lessons = module.get('lessons', [])
        
        if lessons:
            text += "📖 <b>Уроки:</b>\n\n"
            
            buttons = []
            
            for i, lesson in enumerate(lessons, 1):
                lesson_title = lesson.get('title', f'Урок {i}')
                lesson_type = lesson.get('type', 'video')
                
                # Эмодзи в зависимости от типа урока
                type_emoji = {
                    'video': '🎥',
                    'homework': '📝',
                    'test': '✅',
                    'material': '📄'
                }.get(lesson_type, '📖')
                
                # Текст урока
                text += f"{i}. {type_emoji} {lesson_title}\n"
                
                # Кнопка для урока
                buttons.append([InlineKeyboardButton(
                    text=f"{type_emoji} Урок {i}: {lesson_title[:30]}{'...' if len(lesson_title) > 30 else ''}",
                    callback_data=f"mini_lesson_{module_id}_{lesson['id']}"
                )])
            
            text += "\n💡 Нажмите на урок, чтобы начать!"
            
            # Кнопки навигации
            buttons.append([
                InlineKeyboardButton(text="◀️ К мини-курсу", callback_data="my_course_mini_course"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        else:
            text += "📚 Уроки скоро будут добавлены."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К мини-курсу", callback_data="my_course_mini_course")]
            ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_mini_module: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке модуля", show_alert=True)


@router.callback_query(F.data.startswith("mini_lesson_"))
async def show_mini_lesson(callback: CallbackQuery):
    """Показать урок мини-курса"""
    # Формат: mini_lesson_{module_id}_{lesson_id}
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
        # Проверяем доступ к мини-курсу
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
        
        payments = await payment_repo.get_user_payments(user.id)
        payment = next((p for p in payments if p.course_slug == "mini_course" and p.status == 'succeeded' and p.product_type in ['course', 'mini_course']), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к мини-курсу", show_alert=True)
            return
        
        # Получаем урок
        from data import get_mini_course
        from datetime import datetime
        
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
            days_passed = int(time_since_purchase.total_seconds() / 86400)  # 86400 секунд = 24 часа
        else:
            days_passed = 0
        
        is_available = days_passed >= (day_number - 1)
        
        if not is_available:
            await callback.answer("Этот урок пока недоступен", show_alert=True)
            return
        
        # Формируем текст урока
        lesson_type = lesson.get('type', 'video')
        type_emoji = {
            'video': '🎥',
            'homework': '📝',
            'test': '✅',
            'material': '📄'
        }.get(lesson_type, '📖')
        
        text = f"{type_emoji} <b>{lesson['title']}</b>\n\n"
        
        # Описание урока
        description = lesson.get('description', '')
        if description:
            text += f"📝 {description}\n\n"
        
        # Отображение контента урока
        has_content = False
        
        # 1. Видео - через URL или file_id
        video_url = lesson.get('video_url', '')
        if video_url:
            text += f"🎬 <a href='{video_url}'>Смотреть видео</a>\n\n"
            has_content = True
        
        # 2. Текстовое содержание
        text_content = lesson.get('text_content', '')
        if text_content:
            text += f"📝 <b>Содержание урока:</b>\n{text_content}\n\n"
            has_content = True
        
        # Если нет контента
        if not has_content:
            if lesson_type == 'homework':
                text += "✍️ Это домашнее задание для самостоятельной работы.\n\n"
            else:
                text += "🔧 Материалы урока скоро будут добавлены.\n\n"
        
        # Кнопки навигации
        buttons = [
            [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"mini_module_{module_id}")],
            [
                InlineKeyboardButton(text="📚 К мини-курсу", callback_data="my_course_mini_course"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
            ]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in show_mini_lesson: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке урока", show_alert=True)

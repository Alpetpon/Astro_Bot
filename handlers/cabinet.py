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
        courses_count = len([p for p in payments if p.product_type == 'course'])
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
            courses = [p for p in payments if p.product_type == 'course']
            consultations = [p for p in payments if p.product_type == 'consultation']
            
            if courses:
                text += "<b>Курсы:</b>\n"
                for payment in courses:
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
    """Показать мои курсы (заглушка)"""
    await callback.message.edit_text(
        "📚 <b>Мои курсы</b>\n\n"
        "🔧 Раздел находится в разработке.\n"
        "Скоро здесь появятся ваши курсы с доступом к урокам!",
        reply_markup=get_back_keyboard("my_cabinet", "◀️ В кабинет")
    )
    await callback.answer()


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
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type == 'course'), None)
        
        if not payment:
            await callback.answer("У вас нет доступа к этому курсу", show_alert=True)
            return
        
        # Получаем информацию о курсе
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
                lessons_count = len(module.get('lessons', []))
                
                # Краткое название модуля для текста
                text += f"▫️ {module_title}\n"
                text += f"   📖 Уроков: {lessons_count}\n\n"
                
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
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type == 'course'), None)
        
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
                duration = lesson.get('duration', '')
                
                # Эмодзи в зависимости от типа урока
                type_emoji = {
                    'video': '🎥',
                    'homework': '📝',
                    'test': '✅',
                    'material': '📄'
                }.get(lesson_type, '📖')
                
                # Текст урока
                text += f"{i}. {type_emoji} {lesson_title}\n"
                if duration:
                    text += f"   ⏱ {duration}\n"
                
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
        payment = next((p for p in payments if p.course_slug == course_slug and p.status == 'succeeded' and p.product_type == 'course'), None)
        
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
        
        # Длительность
        duration = lesson.get('duration', '')
        if duration and duration != '—':
            text += f"⏱ <b>Длительность:</b> {duration}\n\n"
        
        # Информация о типе контента
        if lesson_type == 'video':
            # Проверяем наличие видео
            video_url = lesson.get('video_url', '')
            file_id = lesson.get('file_id', '')
            
            if video_url:
                text += f"🎬 <a href='{video_url}'>Смотреть видео урока</a>\n\n"
            elif file_id:
                # Отправим видео отдельным сообщением
                try:
                    await callback.message.answer_video(
                        video=file_id,
                        caption=f"{type_emoji} {lesson['title']}"
                    )
                except Exception as e:
                    logger.error(f"Error sending video: {e}")
                    text += "❌ Ошибка при загрузке видео. Обратитесь в поддержку.\n\n"
            else:
                text += "🔧 Видео урока скоро будет добавлено.\n\n"
        
        elif lesson_type == 'homework':
            text += "✍️ Это домашнее задание для самостоятельной работы.\n\n"
        
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
        buttons = [
            [InlineKeyboardButton(text="◀️ К модулю", callback_data=f"module_{course_slug}_{module_id}")],
            [
                InlineKeyboardButton(text="📚 К курсу", callback_data=f"my_course_{course_slug}"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
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
        logger.error(f"Error in show_lesson: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке урока", show_alert=True)

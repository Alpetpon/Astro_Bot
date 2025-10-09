import json
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import and_
from sqlalchemy.orm import Session

from database import (
    get_db, User, Course, Lesson, 
    UserProgress, Payment
)
from keyboards import (
    get_my_cabinet_keyboard,
    get_my_courses_keyboard,
    get_course_progress_keyboard,
    get_lesson_keyboard,
    get_back_keyboard
)

router = Router()


@router.callback_query(F.data == "my_cabinet")
async def show_my_cabinet(callback: CallbackQuery):
    """Показать личный кабинет"""
    db: Session = get_db()
    
    try:
        # Обновляем активность
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        
        # Проверяем, есть ли купленные курсы
        has_courses = db.query(Payment).filter(
            Payment.user_id == user.id,
            Payment.status == 'succeeded'
        ).count() > 0
        
        if has_courses:
            # Получаем статистику
            total_lessons = db.query(UserProgress).filter(
                UserProgress.user_id == user.id
            ).count()
            
            completed_lessons = db.query(UserProgress).filter(
                and_(
                    UserProgress.user_id == user.id,
                    UserProgress.is_completed == True
                )
            ).count()
            
            text = f"🏠 **Мой кабинет**\n\n"
            text += f"👤 {user.first_name or 'Студент'}\n\n"
            text += f"📊 **Статистика:**\n"
            text += f"✅ Пройдено уроков: {completed_lessons} из {total_lessons}\n\n"
            text += "Выберите действие:"
        else:
            text = f"🏠 **Мой кабинет**\n\n"
            text += f"👤 {user.first_name or 'Пользователь'}\n\n"
            text += "У вас пока нет приобретенных курсов.\n"
            text += "Перейдите в раздел «Курсы» для выбора обучения!"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_my_cabinet_keyboard(has_courses),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data == "my_courses")
async def show_my_courses(callback: CallbackQuery):
    """Показать список купленных курсов"""
    db: Session = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        # Получаем курсы пользователя
        payments = db.query(Payment).filter(
            Payment.user_id == user.id,
            Payment.status == 'succeeded'
        ).all()
        
        if not payments:
            await callback.message.edit_text(
                "📚 У вас пока нет приобретенных курсов.",
                reply_markup=get_back_keyboard("my_cabinet", "◀️ Мой кабинет")
            )
            await callback.answer()
            return
        
        # Получаем уникальные курсы
        course_ids = list(set([p.course_id for p in payments]))
        courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
        
        user_courses = [(c.id, c.name) for c in courses]
        
        text = "📚 **Мои курсы**\n\n"
        text += "Выберите курс для продолжения обучения:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_my_courses_keyboard(user_courses),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("my_course_"))
async def show_course_progress(callback: CallbackQuery):
    """Показать прогресс по курсу"""
    course_id = int(callback.data.replace("my_course_", ""))
    
    db: Session = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not course:
            await callback.answer("Курс не найден", show_alert=True)
            return
        
        # Получаем прогресс пользователя
        progress_records = db.query(UserProgress, Lesson).join(
            Lesson, UserProgress.lesson_id == Lesson.id
        ).filter(
            UserProgress.user_id == user.id,
            UserProgress.course_id == course_id
        ).order_by(Lesson.module_number, Lesson.lesson_number).all()
        
        if not progress_records:
            await callback.message.edit_text(
                "❌ Прогресс по курсу не найден.",
                reply_markup=get_back_keyboard("my_courses", "◀️ Мои курсы")
            )
            await callback.answer()
            return
        
        lessons = []
        completed = 0
        total = len(progress_records)
        
        for progress, lesson in progress_records:
            lessons.append({
                'id': lesson.id,
                'module_number': lesson.module_number,
                'lesson_number': lesson.lesson_number,
                'title': lesson.title,
                'is_available': progress.is_available,
                'is_completed': progress.is_completed
            })
            if progress.is_completed:
                completed += 1
        
        text = f"📖 **{course.name}**\n\n"
        text += f"📊 Прогресс: {completed}/{total} уроков\n\n"
        text += "Выберите урок для просмотра:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_course_progress_keyboard(course_id, lessons),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    """Показать урок"""
    # Проверяем, это не материалы
    if callback.data.startswith("lesson_materials_"):
        await show_lesson_materials(callback)
        return
    
    lesson_id = int(callback.data.replace("lesson_", ""))
    
    db: Session = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        # Получаем урок и прогресс
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        progress = db.query(UserProgress).filter(
            and_(
                UserProgress.user_id == user.id,
                UserProgress.lesson_id == lesson_id
            )
        ).first()
        
        if not lesson or not progress:
            await callback.answer("Урок не найден", show_alert=True)
            return
        
        # Проверяем доступность
        if not progress.is_available:
            await callback.answer("🔒 Урок пока недоступен", show_alert=True)
            return
        
        # Обновляем время начала, если урок только начат
        if not progress.started_at:
            progress.started_at = datetime.utcnow()
            user.last_activity = datetime.utcnow()
            db.commit()
        
        # Формируем сообщение урока
        text = f"📖 **Модуль {lesson.module_number}, Урок {lesson.lesson_number}**\n"
        text += f"**{lesson.title}**\n\n"
        
        if lesson.description:
            text += f"{lesson.description}\n\n"
        
        if lesson.duration:
            text += f"⏱ Длительность: {lesson.duration}\n\n"
        
        if lesson.content:
            text += f"📝 **Содержание:**\n{lesson.content}\n\n"
        
        if lesson.video_url:
            text += f"🎥 **Видео:**\n{lesson.video_url}\n\n"
        
        has_materials = bool(lesson.materials)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_lesson_keyboard(lesson_id, lesson.course_id, has_materials),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    finally:
        db.close()


async def show_lesson_materials(callback: CallbackQuery):
    """Показать дополнительные материалы урока"""
    lesson_id = int(callback.data.replace("lesson_materials_", ""))
    
    db: Session = get_db()
    
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson or not lesson.materials:
            await callback.answer("Материалы не найдены", show_alert=True)
            return
        
        text = f"📎 **Дополнительные материалы**\n\n"
        
        try:
            materials = json.loads(lesson.materials)
            for material in materials:
                text += f"• {material}\n"
        except:
            text += lesson.materials
        
        await callback.answer(text, show_alert=True)
    
    finally:
        db.close()


@router.callback_query(F.data.startswith("complete_lesson_"))
async def complete_lesson(callback: CallbackQuery):
    """Завершить урок"""
    lesson_id = int(callback.data.replace("complete_lesson_", ""))
    
    db: Session = get_db()
    
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        # Получаем прогресс
        progress = db.query(UserProgress).filter(
            and_(
                UserProgress.user_id == user.id,
                UserProgress.lesson_id == lesson_id
            )
        ).first()
        
        if not progress:
            await callback.answer("Прогресс не найден", show_alert=True)
            return
        
        # Отмечаем урок как завершенный
        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
            user.last_activity = datetime.utcnow()
            
            # Открываем следующий урок
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            next_lesson = db.query(Lesson).filter(
                Lesson.course_id == lesson.course_id,
                Lesson.order > lesson.order
            ).order_by(Lesson.order).first()
            
            if next_lesson:
                next_progress = db.query(UserProgress).filter(
                    and_(
                        UserProgress.user_id == user.id,
                        UserProgress.lesson_id == next_lesson.id
                    )
                ).first()
                
                if next_progress:
                    next_progress.is_available = True
            
            db.commit()
            
            await callback.answer("✅ Урок завершен! Следующий урок открыт.", show_alert=True)
            
            # Возвращаем к списку уроков курса
            await show_course_progress(callback)
        else:
            await callback.answer("✅ Урок уже завершен", show_alert=True)
    
    except Exception as e:
        print(f"Error in complete_lesson: {e}")
        await callback.answer("Ошибка при завершении урока", show_alert=True)
    
    finally:
        db.close()


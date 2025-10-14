from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy.orm import Session
from sqlalchemy import func
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from config import config
from database import get_db, User, Payment
from data import get_all_courses, get_all_consultations, get_all_guides
from keyboards import get_admin_keyboard, get_back_to_admin_keyboard

router = Router()


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
    """Показать статистику (обновлено для JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db: Session = get_db()
    
    try:
        # Статистика из БД
        total_users = db.query(User).count()
        active_users = db.query(User).filter(
            User.last_activity >= datetime.utcnow() - timedelta(days=30)
        ).count()
        total_payments = db.query(Payment).filter(Payment.status == 'succeeded').count()
        total_revenue = db.query(Payment).filter(Payment.status == 'succeeded').with_entities(
            func.sum(Payment.amount)
        ).scalar() or 0
        
        # Статистика из JSON
        courses = get_all_courses()
        consultations = get_all_consultations()
        guides = get_all_guides()
        
        # Платежи по типам
        course_payments = db.query(Payment).filter(
            Payment.status == 'succeeded',
            Payment.product_type == 'course'
        ).count()
        consultation_payments = db.query(Payment).filter(
            Payment.status == 'succeeded',
            Payment.product_type == 'consultation'
        ).count()
        guide_payments = db.query(Payment).filter(
            Payment.status == 'succeeded',
            Payment.product_type == 'guide'
        ).count()
        
        text = "📊 <b>Статистика</b>\n\n"
        
        text += "👥 <b>Пользователи:</b>\n"
        text += f"  • Всего: {total_users}\n"
        text += f"  • Активных (30 дней): {active_users}\n\n"
        
        text += "💰 <b>Платежи:</b>\n"
        text += f"  • Всего успешных: {total_payments}\n"
        text += f"  • Курсы: {course_payments}\n"
        text += f"  • Консультации: {consultation_payments}\n"
        text += f"  • Гайды: {guide_payments}\n"
        text += f"  • Общая выручка: {total_revenue:,.0f} ₽\n\n"
        
        text += "📚 <b>Контент (JSON):</b>\n"
        text += f"  • Курсов: {len(courses)}\n"
        text += f"  • Консультаций: {len(consultations)}\n"
        text += f"  • Гайдов: {len(guides)}\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()
    
    finally:
        db.close()


@router.callback_query(F.data == "admin_export_users")
async def export_users(callback: CallbackQuery):
    """Экспорт пользователей в Excel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer("⏳ Создаю файл...", show_alert=True)
    
    db: Session = get_db()
    
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        
        # Создаем Excel файл
        wb = Workbook()
        ws = wb.active
        ws.title = "Пользователи"
        
        # Заголовки
        headers = ['ID', 'Telegram ID', 'Username', 'Имя', 'Фамилия', 'Дата регистрации', 'Последняя активность']
        ws.append(headers)
        
        # Стиль заголовков
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
        
        # Данные
        for user in users:
            ws.append([
                user.id,
                user.telegram_id,
                user.username or '-',
                user.first_name or '-',
                user.last_name or '-',
                user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else '-',
                user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else '-'
            ])
        
        # Автоширина колонок
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Сохраняем в BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        # Отправляем файл
        filename = f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        await callback.message.answer_document(
            document=FSInputFile(path=excel_file, filename=filename),
            caption=f"📊 Экспорт пользователей\n\nВсего пользователей: {len(users)}"
        )
        
        await callback.answer("✅ Файл отправлен!")
    
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    
    finally:
        db.close()


@router.callback_query(F.data == "admin_courses")
async def manage_courses_placeholder(callback: CallbackQuery):
    """Управление курсами (теперь через JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    courses = get_all_courses()
    
    text = "📚 <b>Управление курсами</b>\n\n"
    text += f"Всего курсов: {len(courses)}\n\n"
    
    for course in courses:
        emoji = course.get('emoji', '📚')
        status = "✅" if course.get('is_active', True) else "❌"
        text += f"{status} {emoji} {course['name']}\n"
    
    text += "\n💡 <b>Редактирование курсов:</b>\n"
    text += "Курсы хранятся в <code>data/courses.json</code>\n\n"
    text += "Для редактирования:\n"
    text += "1. Откройте файл локально\n"
    text += "2. Внесите изменения\n"
    text += "3. Закоммитьте: <code>git commit -am \"Update courses\"</code>\n"
    text += "4. Задеплойте: <code>git push amvera main:master</code>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_consultations")
async def manage_consultations_placeholder(callback: CallbackQuery):
    """Управление консультациями (теперь через JSON)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    consultations = get_all_consultations()
    
    text = "🔮 <b>Управление консультациями</b>\n\n"
    text += f"Всего консультаций: {len(consultations)}\n\n"
    
    for consultation in consultations[:5]:  # Показываем первые 5
        emoji = consultation.get('emoji', '🔮')
        status = "✅" if consultation.get('is_active', True) else "❌"
        text += f"{status} {emoji} {consultation['name']}\n"
    
    if len(consultations) > 5:
        text += f"\n... и еще {len(consultations) - 5}\n"
    
    text += "\n💡 <b>Редактирование консультаций:</b>\n"
    text += "Консультации хранятся в <code>data/consultations.json</code>\n\n"
    text += "Для редактирования:\n"
    text += "1. Откройте файл локально\n"
    text += "2. Внесите изменения\n"
    text += "3. Закоммитьте: <code>git commit -am \"Update consultations\"</code>\n"
    text += "4. Задеплойте: <code>git push amvera main:master</code>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_admin_keyboard()
    )
    await callback.answer()

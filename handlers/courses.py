from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from database import get_db, UserRepository
from data import get_active_courses, get_course_by_slug, get_tariff_by_id, get_course_modules
from keyboards import (
    get_courses_keyboard,
    get_course_detail_keyboard,
    get_back_keyboard
)

router = Router()


@router.callback_query(F.data == "courses")
async def show_courses_catalog(callback: CallbackQuery):
    """Показать каталог курсов"""
    # Обновляем активность пользователя
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    text = "📚 **Каталог курсов**\n\nВыберите интересующий вас курс:"
    
    # Создаем кнопки с бесплатным курсом первым
    buttons = []
    
    # Добавляем бесплатную инструкцию первой
    buttons.append([InlineKeyboardButton(
        text="🔮 Составь натальную карту бесплатно",
        callback_data="free_natal_chart"
    )])
    
    # Получаем активные курсы из JSON
    courses = get_active_courses()
    
    for course in courses:
        emoji = course.get('emoji', '📚')
        name = course.get('name', '')
        slug = course.get('slug', '')
        
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"course_{slug}"
        )])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        # Если это видео - удаляем и отправляем новое сообщение
        if callback.message.video:
            await callback.message.delete()
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            # Если текст - редактируем
            await callback.message.edit_text(
                text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except Exception:
        # Если не можем отредактировать - удаляем и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("course_register_"))
async def show_tariff_selection(callback: CallbackQuery):
    """Показать выбор тарифа для записи - перенаправление на стоимость"""
    course_slug = callback.data.replace("course_register_", "")
    
    # Создаем mock callback с нужным data
    class CallbackDataWrapper:
        def __init__(self, original_callback, new_data):
            self._original = original_callback
            self.data = new_data
            
        def __getattr__(self, name):
            return getattr(self._original, name)
    
    # Перенаправляем на обработчик стоимости
    wrapped_callback = CallbackDataWrapper(callback, f"course_price_{course_slug}")
    await show_course_price(wrapped_callback)


@router.callback_query(F.data.startswith("course_price_"))
async def show_course_price(callback: CallbackQuery):
    """Показать тарифы курса для выбора"""
    course_slug = callback.data.replace("course_price_", "")
    
    # Получаем курс из JSON
    course = get_course_by_slug(course_slug)
    
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    
    tariffs = course.get('tariffs', [])
    active_tariffs = [t for t in tariffs if t.get('is_active', True)]
    
    if not active_tariffs:
        await callback.answer("Тарифы не найдены", show_alert=True)
        return
    
    # Формируем текст с описанием тарифов
    emoji = course.get('emoji', '📚')
    text = f"💰 **Стоимость курса «{course['name']}»**\n\n"
    
    # Добавляем информацию о каждом тарифе
    for tariff in active_tariffs:
        support_text = "✅ С сопровождением" if tariff.get('with_support') else "📚 Самостоятельно"
        text += f"**{tariff['name']}** — {tariff['price']} ₽\n"
        text += f"{support_text}\n"
        if tariff.get('description'):
            text += f"{tariff['description']}\n"
        
        text += "\nЧто входит:\n"
        if tariff.get('features'):
            for feature in tariff['features']:
                text += f"✔️ {feature}\n"
        
        text += "\n"
    
    text += "Выберите подходящий вам вариант обучения:"
    
    # Создаем кнопки с тарифами
    buttons = []
    for tariff in active_tariffs:
        support_emoji = "👨‍🏫" if tariff.get('with_support') else "📚"
        buttons.append([InlineKeyboardButton(
            text=f"{support_emoji} {tariff['name']} — {tariff['price']} ₽",
            callback_data=f"tariff_{course_slug}_{tariff['id']}"
        )])
    
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("course_"))
async def show_course_detail(callback: CallbackQuery):
    """Показать детальную информацию о курсе - вся информация в одном сообщении"""
    # Извлекаем slug курса
    parts = callback.data.split("_")
    
    if len(parts) < 2:
        await callback.answer("Ошибка при загрузке курса", show_alert=True)
        return
    
    course_slug = "_".join(parts[1:])
    
    # Получаем курс из JSON
    course = get_course_by_slug(course_slug)
    
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    
    # Показываем полную информацию о курсе
    emoji = course.get('emoji', '📚')
    text = f"{emoji} **{course['name']}**\n\n"
    text += f"{course.get('description', '')}\n\n"
    
    if course.get('duration'):
        text += f"⏱ **Длительность:** {course['duration']}\n\n"
    
    if course.get('program'):
        text += "📋 **Программа:**\n"
        for module in course['program']:
            text += f"• {module}\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_course_detail_keyboard(course_slug),
            parse_mode="Markdown"
        )
    except Exception:
        # Если не можем отредактировать (например, это документ, видео или фото)
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_course_detail_keyboard(course_slug),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@router.callback_query(F.data == "free_natal_chart")
async def show_free_natal_chart_block(callback: CallbackQuery):
    """Показать бесплатный блок 'Как построить свою натальную карту' - Урок 1"""
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Пытаемся получить кастомный текст из БД
    from utils.bot_settings import get_setting
    custom_text = await get_setting("free_course_step1_text")
    
    # Если текст не настроен, используем дефолтный
    if not custom_text:
        text = """🔮 Постройте свою натальную карту!

Ниже я предложу вам два варианта, как это сделать, выберите удобный 💫

Это базовый и очень важный шаг, чтобы двигаться дальше.
Без него мы, как вселенские навигаторы без карты 😄

Ваша натальная карта покажет, какие «внутренние персонажи» живут внутри вас — где кто главный, кто любит командовать, а кто шепчет из тени.
Вы узнаете, какие знаки управляют вашими ключевыми сферами от Асцендента (того, как вы себя проявляете) до других важных точек, которые определяют стиль жизни, мышления и отношений."""
    else:
        text = custom_text
    
    # Кнопка "Далее"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Далее ▶️", callback_data="free_natal_chart_step_2")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation")]
    ])
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    await callback.answer()


@router.callback_query(F.data == "free_natal_chart_step_2")
async def show_free_natal_chart_step_2(callback: CallbackQuery):
    """Показать бесплатный блок - Урок 2"""
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Пытаемся получить кастомный текст из БД
    from utils.bot_settings import get_setting
    custom_text = await get_setting("free_course_step2_text")
    
    # Если текст не настроен, используем дефолтный
    if not custom_text:
        text = """💻 Если у вас Windows — рекомендую установить программу ZET 9 (Z9).
Вот ссылка для скачивания https://astrozet.net/

📱 Если нет возможности установить на компьютер — можно пользоваться онлайн-программой Сотис (Sotis-online).
Она работает в любом браузере, даже с телефона https://sotis-online.ru/?chr=ct:1;dt:20250511163725;cid:2417766;name:New%20chart"""
    else:
        text = custom_text
    
    # Кнопки навигации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="free_natal_chart"),
         InlineKeyboardButton(text="Далее ▶️", callback_data="free_natal_chart_step_3")]
    ])
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    await callback.answer()


@router.callback_query(F.data == "free_natal_chart_step_3")
async def show_free_natal_chart_step_3(callback: CallbackQuery):
    """Показать бесплатный блок - Урок 3: Инструкция по Sotis Online"""
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Пытаемся получить кастомный текст из БД
    from utils.bot_settings import get_setting
    custom_text = await get_setting("free_course_step3_text")
    
    # Если текст не настроен, используем дефолтный
    if not custom_text:
        text = """🔮 Инструкция, как построить свою натальную карту в Sotis Online

1️⃣ Открыть сайт
Перейди на сайт → https://sotis-online.ru

2️⃣ Открыть меню
В левом верхнем углу нажми на три полоски (Menu) → появится боковое меню.

3️⃣ Выбрать «Гороскоп» → «Создать новый»
На скрине видно зелёное меню — выбери пункт:
🟢 Создать новый

4️⃣ Выбери тип карты
Появится окно с вариантами.
Выбираем: Одинарная карта
(так строится натальная карта, транзит, дирекции, прогрессии и т.д.)

5️⃣ Ввести данные рождения
Откроется окно с надписью «Изменить».

Заполни поля:
• Тип карты: «Натал»
• Имя: можно написать своё имя или любую подпись (например, Моя карта)
• Дата / Время: 👉 введи свою дату и точное время рождения
  (Если время неизвестно, можно поставить галочку Auto)
• Место: Напиши город рождения, например: Москва, RU

6️⃣ Нажми ОК ✅
После этого программа построит круговую диаграмму — это и есть твоя натальная карта.

7️⃣ (Дополнительно) Сохранить карту
Чтобы не вводить заново:
Открой меню → Гороскоп → Сохранить в базу."""
    else:
        text = custom_text
    
    # Кнопки навигации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="free_natal_chart_step_2"),
         InlineKeyboardButton(text="Далее ▶️", callback_data="free_natal_chart_step_4")]
    ])
    
    try:
        # Пытаемся получить медиа из БД
        from utils.bot_settings import get_setting
        
        # Проверяем наличие фото
        photos_json = await get_setting("free_course_step3_photos")
        video_file_id = await get_setting("free_course_step3_video")
        
        # Удаляем предыдущее сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Если есть видео - отправляем его
        if video_file_id:
            await callback.bot.send_video(
                chat_id=callback.message.chat.id,
                video=video_file_id,
                caption=text,
                reply_markup=keyboard
            )
        # Если есть фото - отправляем их
        elif photos_json:
            import json
            try:
                photos = json.loads(photos_json)
                if photos and len(photos) > 0:
                    # Если одно фото
                    if len(photos) == 1:
                        await callback.bot.send_photo(
                            chat_id=callback.message.chat.id,
                            photo=photos[0],
                            caption=text,
                            reply_markup=keyboard
                        )
                    # Если несколько фото - отправляем группой
                    else:
                        from aiogram.types import InputMediaPhoto
                        media_group = []
                        for i, photo_id in enumerate(photos[:10]):  # Максимум 10 фото
                            if i == 0:
                                media_group.append(InputMediaPhoto(media=photo_id, caption=text))
                            else:
                                media_group.append(InputMediaPhoto(media=photo_id))
                        
                        await callback.bot.send_media_group(
                            chat_id=callback.message.chat.id,
                            media=media_group
                        )
                        # Отправляем кнопки отдельным сообщением
                        await callback.bot.send_message(
                            chat_id=callback.message.chat.id,
                            text="Выберите действие:",
                            reply_markup=keyboard
                        )
                else:
                    # Если массив пустой - просто текст
                    await callback.bot.send_message(
                        chat_id=callback.message.chat.id,
                        text=text,
                        reply_markup=keyboard,
                        disable_web_page_preview=True
                    )
            except:
                # Если ошибка парсинга - просто текст
                await callback.bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=text,
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
        else:
            # Если нет медиа - просто текст
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
    except Exception as e:
        # Если ошибка - показываем текст
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    await callback.answer()


@router.callback_query(F.data == "free_natal_chart_step_4")
async def show_free_natal_chart_step_4(callback: CallbackQuery):
    """Показать бесплатный блок - Шаг 4: Текст + несколько фото"""
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Пытаемся получить кастомный текст из БД
    from utils.bot_settings import get_setting
    custom_text = await get_setting("free_course_step4_text")
    
    # Если текст не настроен, используем дефолтный
    if not custom_text:
        text = """📚 <b>Шаг 4: Дополнительные материалы</b>

Здесь вы найдете полезные материалы и советы для работы с натальной картой.

После изучения материалов переходите к следующему шагу."""
    else:
        text = custom_text
    
    # Кнопки навигации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="free_natal_chart_step_3"),
         InlineKeyboardButton(text="Далее ▶️", callback_data="free_natal_chart_step_5")]
    ])
    
    try:
        # Проверяем наличие фото
        photos_json = await get_setting("free_course_step4_photos")
        
        # Удаляем предыдущее сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        if photos_json:
            import json
            try:
                photos = json.loads(photos_json)
                if photos and len(photos) > 0:
                    # Если одно фото
                    if len(photos) == 1:
                        await callback.bot.send_photo(
                            chat_id=callback.message.chat.id,
                            photo=photos[0],
                            caption=text,
                            reply_markup=keyboard
                        )
                    # Если несколько фото - отправляем группой
                    else:
                        from aiogram.types import InputMediaPhoto
                        media_group = []
                        for i, photo_id in enumerate(photos[:10]):  # Максимум 10 фото
                            if i == 0:
                                media_group.append(InputMediaPhoto(media=photo_id, caption=text))
                            else:
                                media_group.append(InputMediaPhoto(media=photo_id))
                        
                        await callback.bot.send_media_group(
                            chat_id=callback.message.chat.id,
                            media=media_group
                        )
                        # Отправляем кнопки отдельным сообщением
                        await callback.bot.send_message(
                            chat_id=callback.message.chat.id,
                            text="Выберите действие:",
                            reply_markup=keyboard
                        )
                else:
                    # Если массив пустой - просто текст
                    await callback.bot.send_message(
                        chat_id=callback.message.chat.id,
                        text=text,
                        reply_markup=keyboard
                    )
            except:
                # Если ошибка парсинга - просто текст
                await callback.bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=text,
                    reply_markup=keyboard
                )
        else:
            # Если нет фото - просто текст
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=keyboard
            )
    except Exception as e:
        # Если ошибка - показываем текст
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard
        )
    
    await callback.answer()


@router.callback_query(F.data == "free_natal_chart_step_5")
async def show_free_natal_chart_step_5(callback: CallbackQuery):
    """Показать бесплатный блок - Шаг 5: Текст + одно фото"""
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Пытаемся получить кастомный текст из БД
    from utils.bot_settings import get_setting
    custom_text = await get_setting("free_course_step5_text")
    
    # Если текст не настроен, используем дефолтный
    if not custom_text:
        text = """🎯 <b>Шаг 5: Подсказки по символам</b>

Важные символы и их значения в натальной карте.

Это поможет вам лучше ориентироваться при чтении карты."""
    else:
        text = custom_text
    
    # Кнопка "Получилось" и назад
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Получилось", callback_data="natal_chart_done")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="free_natal_chart_step_4")]
    ])
    
    try:
        # Проверяем наличие фото
        photo_file_id = await get_setting("free_course_step5_photo")
        
        # Удаляем предыдущее сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        if photo_file_id:
            # Если есть фото - отправляем его с текстом
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo_file_id,
                caption=text,
                reply_markup=keyboard
            )
        else:
            # Если нет фото - просто текст
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=keyboard
            )
    except Exception as e:
        # Если ошибка - показываем текст
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard
        )
    
    await callback.answer()


@router.callback_query(F.data == "natal_chart_done")
async def natal_chart_done(callback: CallbackQuery):
    """Обработчик кнопки 'Получилось' - показываем три пути"""
    db = await get_db()
    user_repo = UserRepository(db)
    await user_repo.update_activity(callback.from_user.id)
    
    # Пытаемся получить текст из БД
    from utils.bot_settings import get_setting
    
    custom_text = await get_setting("free_course_final_message")
    
    # Если текст не настроен, используем дефолтный
    if not custom_text:
        text = """✨ Теперь, когда вы знаете свою натальную карту, самое время идти дальше!

Я предлагаю три пути (выбирайте по уровню смелости 😄):

💞 Если вы уже немного знакомы с астрологией и хотите глубже понять сценарии отношений — вас ждёт курс LoveCode. Он о том, почему отношения складываются именно так и как их переписать через понимание своей карты.

🌱 Если вы только начинаете знакомство с собой через астрологию — начните с мини-курса «7 дней самопознания». Он лёгкий, с юмором и даёт почувствовать магию астрологии без перегруза терминами.

🚀 А если вы решительно настроены и чувствуете, что готовы сразу нырнуть в глубину, — добро пожаловать на «Основы астропсихологии».
Это полноценное обучение, где вы научитесь читать карты как профессионал и понимать себя без мистики, но с душой."""
    else:
        text = custom_text
    
    # Кнопки для выбора пути
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💞 LoveCode", callback_data="course_love-code")],
        [InlineKeyboardButton(text="🌱 Мини-курс (7 дней)", callback_data="mini_course")],
        [InlineKeyboardButton(text="🚀 Основы астропсихологии", callback_data="course_astro-basics")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_navigation"), 
         InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
    ])
    
    # Проверяем наличие фото для финального сообщения
    photo_file_id = await get_setting("free_course_final_photo")
    
    try:
        # Удаляем предыдущее сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        if photo_file_id:
            # Если есть фото - отправляем его с текстом
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo_file_id,
                caption=text,
                reply_markup=keyboard
            )
        else:
            # Если нет фото - просто текст
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=keyboard
            )
    except Exception:
        # Если ошибка - показываем текст
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard
        )
    
    await callback.answer()

# Управление данными через JSON и Админ-панель

## 🎯 Новая архитектура

После миграции **ВСЕ** данные (курсы, консультации, гайды) хранятся в **JSON файлах** и редактируются через **Админ-панель**.

### Что где хранится

```
📁 data/                          # Статичные данные (JSON)
  ├── courses.json                # Курсы с тарифами
  ├── consultations.json          # Консультации с опциями  
  └── guides.json                 # Гайды

💾 database/                      # Динамические данные (БД)
  └── models.py                   # ТОЛЬКО User + Payment
```

## ✅ Преимущества нового подхода

1. **Не обнуляется при перезапуске** - данные в JSON не зависят от БД
2. **Легко редактировать** - через админ-панель бота
3. **Git-friendly** - изменения видны в истории коммитов
4. **Резервные копии** - автоматически в репозитории
5. **Быстрый доступ** - не нужны запросы к БД

## 📝 Как редактировать данные

### Через Админ-панель (рекомендуется)

1. Откройте бота
2. Нажмите `/admin`
3. Выберите раздел:
   - **💝 Гайды** - создать/редактировать/удалить гайды
   - **📚 Курсы** (скоро) - управление курсами
   - **🔮 Консультации** (скоро) - управление консультациями

### Напрямую через JSON (продвинутые)

Вы можете редактировать JSON файлы напрямую:

```bash
cd /Users/alex/Downloads/Work/Разработка/Astro_Bot/data
nano courses.json           # Редактировать курсы
nano consultations.json     # Редактировать консультации
nano guides.json            # Редактировать гайды
```

После редактирования:
```bash
git add data/
git commit -m "Обновлены данные"
git push amvera main:master
```

## 📖 Структура данных

### Гайд (guides.json)

```json
{
  "id": "relationships",
  "name": "Гайд по отношениям",
  "emoji": "💕",
  "description": "Описание гайда в Markdown",
  "file_id": "BQACAgIAAxkBAAIC...",
  "related_course_slug": "love-code",
  "is_active": true,
  "order": 1
}
```

### Курс (courses.json)

```json
{
  "id": "astro-basics",
  "name": "Основы астропсихологии",
  "slug": "astro-basics",
  "emoji": "🌞",
  "description": "Полное описание курса",
  "short_description": "Краткое описание",
  "program": ["Модуль 1", "Модуль 2"],
  "duration": "3 месяца",
  "is_active": true,
  "order": 1,
  "tariffs": [
    {
      "id": "astro-basics-solo",
      "name": "Самостоятельное обучение",
      "price": 25000,
      "with_support": false,
      "features": ["Особенность 1", "Особенность 2"],
      "is_active": true,
      "order": 1
    }
  ]
}
```

### Консультация (consultations.json)

```json
{
  "id": "natal-chart-full",
  "name": "Полный разбор натальной карты",
  "slug": "natal-chart-full",
  "emoji": "🌟",
  "short_description": "Краткое описание",
  "for_whom": "Для кого это",
  "what_included": ["Что входит 1", "Что входит 2"],
  "format_info": "Формат работы",
  "result": "Результат на выходе",
  "price": 13800,
  "duration": "90-120 минут",
  "is_active": true,
  "order": 1,
  "category": "consultation",
  "options": [
    {
      "id": "option-1",
      "name": "Вариант 1",
      "price": 10000,
      "duration": "60 минут",
      "features": ["Фича 1", "Фича 2"],
      "is_active": true,
      "order": 1
    }
  ]
}
```

## 🛠 API для разработчиков

Если вы хотите программно работать с данными:

```python
from data import (
    # Чтение
    get_all_courses,
    get_course_by_slug,
    get_all_consultations,
    get_consultation_by_slug,
    get_all_guides,
    get_guide_by_id,
    
    # Запись
    save_course,
    save_consultation,
    save_guide,
    
    # Удаление
    delete_course,
    delete_consultation,
    delete_guide
)

# Пример: получить все курсы
courses = get_all_courses()

# Пример: создать новый гайд
new_guide = {
    'id': 'my-guide',
    'name': 'Мой новый гайд',
    'emoji': '✨',
    'description': 'Описание...',
    'file_id': None,
    'related_course_slug': None,
    'order': 1,
    'is_active': True
}
save_guide(new_guide)
```

## 🚀 Деплой изменений

После редактирования данных:

```bash
git add data/
git commit -m "Обновлены гайды/курсы/консультации"
git push amvera main:master     # Деплой на продакшн
git push origin main             # Бэкап на GitHub
```

Изменения применятся **немедленно** после перезапуска бота на Amvera.

## ⚠️ Важные замечания

1. **ID должен быть уникальным** - используйте латиницу и дефисы
2. **Порядок (order)** - определяет последовательность показа
3. **is_active** - если false, элемент не показывается пользователям
4. **Валидация JSON** - проверяйте корректность перед коммитом
5. **Бэкапы** - Git автоматически сохраняет все версии

## 📊 База данных (SQLite)

В БД остались **ТОЛЬКО**:
- ✅ `users` - пользователи бота
- ✅ `payments` - платежи (с ссылками на slug курсов/консультаций)

**НЕТ В БД:**
- ❌ `courses` - теперь в JSON
- ❌ `tariffs` - теперь в JSON
- ❌ `consultations` - теперь в JSON
- ❌ `consultation_options` - теперь в JSON
- ❌ `guides` - теперь в JSON
- ❌ `lessons` - удалены

## 🔄 Синхронизация локально и на сервере

Файлы JSON синхронизируются через Git:

**Локально → Сервер:**
```bash
# 1. Редактируйте JSON локально
# 2. Закоммитьте и запушьте
git add data/
git commit -m "Update data"
git push amvera main:master
```

**Сервер → Локально:**
```bash
git pull origin main
```

## 🎓 Планы на будущее

- [ ] Админ-панель для редактирования курсов
- [ ] Админ-панель для редактирования консультаций
- [ ] Валидация данных при сохранении
- [ ] История изменений в админке
- [ ] Экспорт/импорт данных

---

**Вопросы?** Все данные теперь прозрачны и легко редактируются! 🎉


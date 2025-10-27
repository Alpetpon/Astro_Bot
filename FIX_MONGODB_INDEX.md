# Исправление ошибки индекса MongoDB

## Проблема
```
E11000 duplicate key error collection: astro_bot.payments index: payment_id_1 dup key: { payment_id: null }
```

Эта ошибка возникает, когда в MongoDB есть старый уникальный индекс на поле `payment_id` без параметра `sparse`. Это не позволяет создавать несколько записей с `payment_id: null`.

## Решение

### Вариант 1: Через скрипт (рекомендуется)

1. Запустите скрипт миграции на сервере:
```bash
python fix_payment_index.py
```

Скрипт автоматически:
- Удалит старый индекс
- Создаст новый sparse индекс
- Проверит результат

### Вариант 2: Вручную через MongoDB Shell

1. Подключитесь к MongoDB:
```bash
mongosh mongodb://localhost:27017/astro_bot
# или если с аутентификацией:
mongosh mongodb://admin:password@localhost:27017/astro_bot?authSource=admin
```

2. Проверьте текущие индексы:
```javascript
db.payments.getIndexes()
```

3. Удалите старый индекс:
```javascript
db.payments.dropIndex("payment_id_1")
```

4. Создайте новый sparse индекс:
```javascript
db.payments.createIndex({ payment_id: 1 }, { unique: true, sparse: true })
```

5. Проверьте результат:
```javascript
db.payments.getIndexes()
```

Должен быть индекс:
```json
{
  "v": 2,
  "key": { "payment_id": 1 },
  "name": "payment_id_1",
  "unique": true,
  "sparse": true
}
```

### Вариант 3: Через Docker (если используется Docker)

```bash
# Войдите в контейнер MongoDB
docker exec -it astro_bot_mongodb mongosh -u admin -p admin_password_change_me

# Выполните команды из Варианта 2
```

## Проверка

После исправления индекса перезапустите бота:
```bash
# Если запущен напрямую
pkill -f bot.py
python bot.py

# Если через Docker
docker-compose restart sales_bot learning_bot
```

## Что такое sparse индекс?

**Sparse индекс** игнорирует документы, где индексируемое поле отсутствует или равно `null`. Это позволяет:
- Иметь несколько документов с `payment_id: null`
- Сохранить уникальность для не-null значений

В нашем случае это правильно, потому что:
1. Платеж создается в БД сначала без `payment_id` (он еще null)
2. После создания платежа в ЮКассе, `payment_id` заполняется уникальным значением
3. Все не-null значения `payment_id` остаются уникальными

## Важно

После исправления индекса проблема больше не должна возникать. Все новые платежи будут создаваться корректно.


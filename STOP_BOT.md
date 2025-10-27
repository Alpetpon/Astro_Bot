# Остановка бота

## Если бот запущен через Docker Compose

```bash
# Остановить все контейнеры
docker-compose down

# Или остановить только боты (оставив MongoDB)
docker-compose stop sales_bot learning_bot
```

## Если бот запущен на Amvera

Зайдите в панель управления Amvera и остановите проект через интерфейс.

Или через CLI:
```bash
amvera stop
```

## Если бот запущен напрямую (без Docker)

```bash
# Найти процессы
ps aux | grep bot.py

# Остановить все процессы бота
pkill -f "bot.py"
pkill -f "learning_bot.py"

# Или по конкретному PID
kill <PID>
```

## Если бот запущен через systemd

```bash
# Остановить сервис
sudo systemctl stop astro_bot

# Проверить статус
sudo systemctl status astro_bot
```

## Если бот запущен через screen/tmux

```bash
# Посмотреть активные сессии screen
screen -ls

# Подключиться к сессии
screen -r <session_name>

# Остановить бот (Ctrl+C)

# Или убить сессию
screen -X -S <session_name> quit
```

## Проверка остановки

```bash
# Проверить, что процессы остановлены
ps aux | grep bot.py
ps aux | grep learning_bot.py

# Проверить Docker контейнеры
docker ps | grep bot
```

Все процессы должны быть остановлены.


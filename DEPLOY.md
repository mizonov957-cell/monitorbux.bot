# Деплой бота

## На Heroku

1. Создайте аккаунт на [Heroku](https://heroku.com)
2. Установите Heroku CLI
3. Выполните команды:

```bash
heroku login
heroku create your-bot-name
heroku config:set BOT_TOKEN=your_token
heroku config:set ADMIN_ID=your_admin_id
git push heroku main
```

## На другом хостинге

1. Загрузите файлы проекта
2. Установите Python 3.11+
3. Установите зависимости: `pip install -r requirements.txt`
4. Настройте переменные окружения
5. Запустите: `python bot.py`

## Переменные окружения

Обязательно настройте:
- `BOT_TOKEN` — токен от @BotFather
- `ADMIN_ID` — ваш Telegram ID

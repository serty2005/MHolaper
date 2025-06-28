#!/bin/bash
# Этот скрипт запускается при старте контейнера.
# Он выполняет миграции базы данных перед запуском Gunicorn.

echo "Running database migrations..."
# Убедимся, что мы находимся в рабочей директории приложения
cd /opt/olaper

# Выполняем миграции. Команда 'flask db upgrade' создаст таблицы, если их нет,
# и применит любые ожидающие миграции.
# '--app app' указывает Flask CLI использовать экземпляр приложения 'app' из app.py
flask --app app db upgrade

# Проверяем код выхода предыдущей команды
if [ $? -ne 0 ]; then
  echo "Database migration failed!"
  exit 1
fi

echo "Database migrations applied successfully."
echo "Starting Gunicorn server..."

# Запускаем Gunicorn. Используем 'exec' чтобы сигналы (например, SIGTERM)
# передавались напрямую процессу Gunicorn.
exec gunicorn --bind 0.0.0.0:5005 app:app
# Используем официальный образ Python
FROM python:3.9-slim-buster

# Устанавливаем переменные окружения для нечувствительных настроек
ENV DATA_DIR=/opt/olaper/data
ENV DATABASE_URL="sqlite:///${DATA_DIR}/app.db"
# SECRET_KEY и ENCRYPTION_KEY ДОЛЖНЫ БЫТЬ ПРЕДОСТАВЛЕНЫ ВО ВРЕМЯ ЗАПУСКА!

# Устанавливаем рабочую директорию в контейнере
WORKDIR /opt/olaper

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

RUN chmod +x /opt/olaper/start.sh

# Убеждаемся, что директория для данных существует
RUN mkdir -p ${DATA_DIR}

# Открываем порт, на котором будет работать Gunicorn
EXPOSE 5005

# Запускаем скрипт старта
CMD ["/opt/olaper/start.sh"]
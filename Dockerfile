# Используем образ Python 3.10 из зеркала Google Container Registry
FROM mirror.gcr.io/library/python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями в рабочую директорию
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта в рабочую директорию контейнера
COPY . .

# Открываем порт, если это необходимо для вашего приложения (например, для веб-сервера)
# EXPOSE 8000

# Команда для запуска вашего скрипта при запуске контейнера
CMD ["python", "scripts/yandex_llm.py"]

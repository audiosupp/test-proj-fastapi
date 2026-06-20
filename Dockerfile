FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /code

# Копируем файл зависимостей
COPY ./requirements.txt /code/requirements.txt

# Устанавливаем библиотеки Python
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Копируем весь остальной код проекта в контейнер
COPY . .

# Гарантируем, что папка storage существует внутри контейнера
RUN mkdir -p /code/app/storage

# Hugging Face Spaces требует, чтобы приложение работало строго на порту 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

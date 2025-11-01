# Используем официальный образ Python
FROM python:3.12-bookworm

# Шаг 1: базовые инструменты
RUN apt-get update && apt-get install -y \
    build-essential curl wget ca-certificates \
    --no-install-recommends && rm -rf /var/lib/apt/lists/* && apt-get clean

# Шаг 2: шрифты и иконки
RUN apt-get update && apt-get install -y \
    fonts-liberation libnss3 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/* && apt-get clean

# Шаг 3: библиотеки для графики и звука
RUN apt-get update && apt-get install -y \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/* && apt-get clean

RUN apt-get update && apt-get install -y \
    libgbm1 libpango-1.0-0 libasound2 \
    libwayland-client0 libwayland-server0 libgtk-3-0 libpangocairo-1.0-0 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/* && apt-get clean

# Задаём рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium

# Копируем код бота в рабочую директорию
COPY bot/ ./

# Указываем переменную окружения для корректного вывода
ENV PYTHONUNBUFFERED=1

# Точка входа
CMD ["python", "main.py"]
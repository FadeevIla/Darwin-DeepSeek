FROM python:3.11.9-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Скрипт запуска с убийством старых процессов
RUN echo '#!/bin/bash\n\
echo "🔪 Убиваю старые процессы бота..."\n\
pkill -f "bot.py" 2>/dev/null || true\n\
sleep 2\n\
echo "🚀 Запускаю нового бота..."\n\
exec python bot.py' > /entrypoint.sh && chmod +x /entrypoint.sh

# Для Web Service - слушаем порт
EXPOSE 10000

# Добавляем healthcheck для Render
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/health')" || exit 1

CMD ["/entrypoint.sh"]
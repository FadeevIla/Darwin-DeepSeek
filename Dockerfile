FROM python:3.11.9-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 🆕 Автофикс импортов перед запуском
RUN python -c "from core.import_fixer import fix_all_imports; fix_all_imports()"

# Для Web Service - слушаем порт
EXPOSE 10000

# Добавляем healthcheck для Render
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/health')" || exit 1

CMD ["python", "bot.py"]
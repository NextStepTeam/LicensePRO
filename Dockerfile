FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Создаем скрипт для запуска с ожиданием БД
RUN echo '#!/bin/bash\n\
echo "Waiting for PostgreSQL to be ready..."\n\
# Ждем пока PostgreSQL станет доступен\n\
for i in {1..30}; do\n\
  if curl -s postgres:5432 >/dev/null 2>&1; then\n\
    echo "PostgreSQL is ready!"\n\
    break\n\
  fi\n\
  echo "Attempt $i/30: PostgreSQL not ready, waiting..."\n\
  sleep 2\n\
done\n\
# Запускаем Flask приложение\n\
echo "Starting Flask application..."\n\
exec python run.py\n\
' > /app/start.sh && chmod +x /app/start.sh

ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Используем скрипт как точку входа
CMD ["/app/start.sh"]
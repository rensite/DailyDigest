FROM python:3.12-slim

WORKDIR /app

# tzdata нужен для корректной работы планировщика по таймзоне
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# По умолчанию: веб-сервер + встроенный планировщик
CMD ["python", "main.py", "serve"]

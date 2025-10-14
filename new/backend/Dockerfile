FROM python:3.10-slim

# System deps for pdf2image and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
  poppler-utils libjpeg62-turbo-dev zlib1g-dev libfreetype6-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code
COPY . /app

ENV PYTHONUNBUFFERED=1
CMD uvicorn config.asgi:application --host 0.0.0.0 --port $PORT

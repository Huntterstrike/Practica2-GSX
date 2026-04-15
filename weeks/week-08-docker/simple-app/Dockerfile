FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

RUN addgroup -S app && adduser -S app -G app

COPY app.py .

RUN mkdir -p /data && chown app:app /data

# Instalar redis client
RUN pip install --no-cache-dir redis

USER app

EXPOSE 5000

CMD ["python", "app.py"]
FROM simple-app-gsx:latest

USER root

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

USER app

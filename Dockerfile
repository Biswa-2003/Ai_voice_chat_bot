FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

ENV PORT=8000 \
    LOG_LEVEL=INFO \
    SCENARIO=presale \
    DEFAULT_LANGUAGE=en \
    LOG_DIR=logs \
    TTS_PROVIDER=sarvam

EXPOSE 8000

CMD ["python", "token_server.py"]

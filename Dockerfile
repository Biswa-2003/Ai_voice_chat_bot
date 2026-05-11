FROM python:3.11-slim

WORKDIR /app

# System deps for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

ENV SCENARIO=presale \
    DEFAULT_LANGUAGE=en \
    LOG_DIR=logs \
    LOG_LEVEL=INFO

CMD ["python", "-m", "src.main", "start"]

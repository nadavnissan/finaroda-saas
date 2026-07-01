# Dockerfile — alternate deploy path for FINARODA backend (Railway uses nixpacks by default).
FROM python:3.13-slim

# System deps: curl (litestream download), build-essential (cryptography C ext).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Litestream binary (SQLite → R2 replication).
ARG LITESTREAM_VERSION=0.3.13
RUN curl -L -o /tmp/litestream.tar.gz \
    https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-v${LITESTREAM_VERSION}-linux-amd64.tar.gz \
    && tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz \
    && rm /tmp/litestream.tar.gz

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

RUN mkdir -p /app/data
COPY . /app
COPY litestream.yml /etc/litestream.yml

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# R2_* env vars come from the Railway dashboard.
CMD ["sh", "-c", "litestream replicate -config /etc/litestream.yml -exec \"uvicorn backend.main:app --host 0.0.0.0 --port $PORT\""]

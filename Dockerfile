FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Railway routes public HTTPS traffic to $PORT inside the container, so the app
# must listen on all container interfaces here. Locally HOST defaults to
# 127.0.0.1. Every route is gated: Shopify HMAC (OAuth, webhooks), App Bridge
# session tokens (/api), or a single-use expiring link (/c). The app refuses to
# start on a non-loopback host unless every secret is set (config.check_deployable).
ENV HOST=0.0.0.0
# SQLite lives on a Railway volume mounted at /data, so it survives redeploys.
# Railway mounts volumes as root, so the process runs as root to write there.
ENV CODGUARD_DB=/data/codguard.sqlite3

CMD ["python", "-m", "app"]

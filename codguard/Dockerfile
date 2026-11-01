FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app/ holds the address scorer; website/ is the site that serves it.
# (app/ also contains the earlier Shopify-app code, which this image does not run.)
COPY app/ ./app/
COPY website/ ./website/

# Railway routes public HTTPS traffic to $PORT inside the container, so listen on
# all container interfaces here; locally HOST defaults to 127.0.0.1. Public routes
# are the marketing page and a rate-limited free checker; paid routes require a
# Lemon Squeezy license key verified with Lemon Squeezy. The site refuses to start
# on a public host without SITE_URL=https://... and the Lemon Squeezy store config.
ENV HOST=0.0.0.0
# Only a monthly usage counter lives here; mount a Railway volume at /data to keep it.
ENV CODGUARD_DB=/data/codguard-web.sqlite3
RUN mkdir -p /data

CMD ["python", "-m", "website"]

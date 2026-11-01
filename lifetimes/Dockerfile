FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ ./server/
COPY public/ ./public/
# Railway routes public traffic to $PORT inside the container. The site is a public
# game; the only API is /api/unlock, which verifies Lemon Squeezy keys and is rate limited.
ENV HOST=0.0.0.0
CMD ["python", "-m", "server"]

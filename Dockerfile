# Container for Render (or any Docker host). Includes Chromium for the table image.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends fonts-khmeros && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-postgres.txt ./
RUN pip install -r requirements.txt -r requirements-postgres.txt && playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
COPY . .
ENV HOST=0.0.0.0 TRUST_PROXY=1 COOKIE_SECURE=1
EXPOSE 10000
CMD ["python", "app.py"]

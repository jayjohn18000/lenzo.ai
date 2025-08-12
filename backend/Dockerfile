# Python runtime
FROM python:3.11-slim

WORKDIR /app

# System deps (add build-essential if you compile libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

# Copy minimal first for better layer caching
COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the backend code
COPY . /app

# Default envs (override via .env / compose)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

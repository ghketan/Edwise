FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MALLOC_ARENA_MAX=2

WORKDIR /app

# Install system dependencies if needed (e.g. for building/compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies (supports build context from root or backend)
COPY requirements.txt* backend/requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else pip install --no-cache-dir -r backend/requirements.txt; fi

# Copy backend application source
COPY . .

# Expose port
EXPOSE 8000

# Automatically run seed migrations on boot, then start uvicorn
CMD ["sh", "-c", "python backend/seed_data.py || true; uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]


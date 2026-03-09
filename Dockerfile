# Stage 1: Build frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.13-slim
WORKDIR /app

# Install system dependencies for OpenCV + wget for model downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ backend/
COPY alembic_migrations/ alembic_migrations/
COPY alembic.ini .

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Entrypoint downloads models on first run if not already mounted
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

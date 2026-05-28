# ==========================================
# Stage 1: Build the Next.js Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build static export
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Build the FastAPI Backend
# ==========================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY . .

# Copy the built static frontend from Stage 1 into the backend's static folder
RUN rm -rf static && mkdir -p static
COPY --from=frontend-builder /app/frontend/out/ ./static/

EXPOSE 8000
RUN chmod +x start.sh

CMD ["./start.sh"]

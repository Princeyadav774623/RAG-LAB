FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables to avoid python generating .pyc and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# gcc/g++ are often needed for compiling some python ML/database packages like psycopg2 or sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Make the start script executable
RUN chmod +x start.sh

# Run the startup script
CMD ["./start.sh"]

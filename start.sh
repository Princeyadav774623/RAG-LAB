#!/bin/bash
# Production Startup Script

# We use uvicorn with a worker count depending on available cores, or default to 2
# It is important NOT to use --reload in production.
echo "Starting Uvicorn for production..."
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2

# ============================================================================
# Render.com Deployment — FastAPI + Frontend + Managed PostgreSQL
# ============================================================================
# Serves both the API and the frontend from a single container
# ============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY schema/ ./schema/
COPY frontend/ ./frontend/

EXPOSE 10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "2"]

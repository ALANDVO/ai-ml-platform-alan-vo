FROM python:3.12-slim

# Create nonroot user
RUN useradd -u 10001 -m -s /bin/bash appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENV PYTHONPATH=/app/app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s CMD curl -f http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

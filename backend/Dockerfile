FROM python:3.11-slim

# Create a non-root user to run the application
RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# Install Python dependencies (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Give the non-root user ownership of the working directory
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Smoke-test the health endpoint once the server is up
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# 2 workers is safe for containers with ≥1 vCPU; adjust via UVICORN_WORKERS env var
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}"]


FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (for docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY machadb /app/machadb
COPY static /app/static
COPY server.py /app/server.py
COPY README.md /app/README.md

# Make sure the data directory exists
RUN mkdir -p /app/machadb_data

# Set environment variable so server.py knows where to put data
ENV MACHADB_DATA_DIR=/app/machadb_data

# Expose the API port
EXPOSE 8000

# Run with exactly 1 worker to avoid concurrency file corruption!
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

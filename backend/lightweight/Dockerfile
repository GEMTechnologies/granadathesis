FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for weasyprint
RUN apt-get update && apt-get install -y \
    libgobject-2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core /app/core
COPY workers /app/workers
COPY agents /app/agents
COPY services /app/services
COPY api.py /app/

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["python", "api.py"]

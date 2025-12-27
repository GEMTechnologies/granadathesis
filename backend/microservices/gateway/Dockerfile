FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY ../shared /app/shared

# Copy gateway code
COPY main.py /app/

# Expose port
EXPOSE 8000

# Run gateway
CMD ["python", "main.py"]

FROM python:3.9-slim

# Install netcat for database healthcheck
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

# Copy application code
COPY . .

# Create data directory for ingredients
RUN mkdir -p /app/data

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

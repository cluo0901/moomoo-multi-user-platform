FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1001 appuser

# Set working directory
WORKDIR /app

# Copy moomoo OpenD (you would need to download this)
# This is a placeholder - in production you'd need the actual OpenD binary
RUN mkdir -p /app/opend
# COPY opend/ /app/opend/

# Install Python dependencies
COPY requirements-connector.txt .
RUN python3 -m pip install --no-cache-dir -r requirements-connector.txt

# Copy connector application
COPY connector/ /app/connector/
COPY data_sync.py /app/
COPY currency_converter.py /app/
COPY models.py /app/

# Create config directory
RUN mkdir -p /app/config && chown appuser:appuser /app/config

# Switch to app user
USER appuser

# Expose ports
EXPOSE 11111 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["python3", "/app/connector/main.py"]
# OpenD Connector Container
# Runs OpenD with API wrapper for each user
FROM python:3.9-slim

# Install system dependencies including libfuse2 for OpenD
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    procps \
    build-essential \
    libfuse2 \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories
RUN mkdir -p /app/config /app/logs /app/opend /app/templates /app/scripts

# Download and install real OpenD binary
# NOTE: This is a placeholder for manual OpenD binary installation
# The real OpenD binary needs to be manually downloaded from moomoo and placed here
# Instructions for manual installation:
# 1. Download OpenD for Ubuntu from: https://www.moomoo.com/us/support/topic3_441
# 2. Extract the archive and copy OpenD binary and Appdata.dat to /app/opend/
# 3. The binary should be named 'OpenD' and be executable
RUN echo '#!/bin/bash\n\
echo "NOTICE: This is a placeholder for real OpenD binary"\n\
echo "Please replace this container with one containing the actual OpenD binary"\n\
echo "Download OpenD from: https://www.moomoo.com/us/support/topic3_441"\n\
echo "Copy OpenD binary and Appdata.dat to /app/opend/"\n\
echo "OpenD binary should be executable and named OpenD"\n\
echo "Current placeholder will exit in 10 seconds"\n\
sleep 10\n\
echo "Placeholder OpenD exiting - real binary required for production"' > /app/opend/OpenD \
    && chmod +x /app/opend/OpenD \
    && echo "PLACEHOLDER_BINARY=true" > /app/opend/binary_status

# Copy connector service and configuration files
COPY connector_service.py .
COPY templates/ /app/templates/
COPY scripts/ /app/scripts/

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

# Create non-root user with proper groups
RUN useradd --create-home --shell /bin/bash --uid 1000 opend \
    && chown -R opend:opend /app

# Switch to non-root user
USER opend

# Expose ports
EXPOSE 8000 11111

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production startup with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "connector_service:app"]
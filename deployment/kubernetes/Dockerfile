# Multi-stage Dockerfile for all services
# Optimized for size and security

# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy optimized requirements and install dependencies
COPY requirements-optimized.txt requirements.txt
RUN pip install --user --no-cache-dir --no-warn-script-location \
    -r requirements.txt

# Stage 2: Runtime - Minimal image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Copy installed packages from builder to appuser's home
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser services/ ./services/

# Create data directory
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Add local packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose ports (specific service defines which)
EXPOSE 8010 8011 8012 8013 8014 8015 8016 8017 8020

# Default command (override in K8s manifests)
CMD ["python", "-u", "services/api_gateway.py"]


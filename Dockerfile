# Use uv-based Python image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using uv
RUN uv sync

# Copy application files
COPY weather-server.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# Create directory for database
RUN mkdir -p /app/db

# Expose Flask port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "-m", "007", "weather-server:app"]

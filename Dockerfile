FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies (CPU-only torch to keep image size small)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    tweepy>=4.14.0 \
    schedule>=1.2.0 \
    numpy>=1.22.0 \
    python-dotenv>=1.0.0 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch>=2.0.0

# Copy application files
COPY growth_engine.py .

# Run with unbuffered output
ENV PYTHONUNBUFFERED=1

CMD ["python", "growth_engine.py"]

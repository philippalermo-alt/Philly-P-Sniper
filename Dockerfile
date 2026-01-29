FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Ensure root directory is in PYTHONPATH for module imports
ENV PYTHONPATH=/app

# Install system dependencies
# libpq-dev is for psycopg2 (Postgres)
# build-essential is for compiling if needed
# git and curl are generally useful
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Copy startup script
COPY start_dashboard.sh .
RUN chmod +x start_dashboard.sh

# Default command matches start_dashboard.sh
CMD ["./start_dashboard.sh"]

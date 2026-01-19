FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# libpq-dev is for psycopg2 (Postgres)
# build-essential is for compiling if needed
# git and curl are generally useful
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Default command (can be overridden in docker-compose)
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
COPY lib/ ./lib/
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir lib/py_marquee_heartbeat-*.whl

# Copy web files
COPY src/ .

# Expose port
EXPOSE 8888

# Run the Flask web server
# Set environment variables for credentials:
# ADMIN_USERNAME=your_username
# ADMIN_PASSWORD=your_password
# SECRET_KEY=your_secret_key (optional, auto-generated if not set)
CMD ["python3", "server.py"]

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy web files
COPY . .

# Expose port
EXPOSE 8888

# Run the web server
CMD ["python3", "-m", "http.server", "8888"]

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service file
COPY marquee_launcher_service.py .

# Copy necessary modules and scripts from cli directory
RUN mkdir -p cache
RUN mkdir -p cli
COPY cli.tar.gz .
RUN tar -xvzf cli.tar.gz

# Run the service
CMD ["python", "marquee_launcher_service.py"]

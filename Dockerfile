# Dockerfile for Code Reviewer Environment
# Deploys to Hugging Face Spaces

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (HF Spaces uses 7860 by default)
EXPOSE 7860

# Set environment variables
ENV PORT=7860
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "server.py"]

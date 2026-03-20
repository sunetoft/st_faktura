# ST_Faktura - Google Cloud Run Dockerfile
FROM node:20-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN node ./node_modules/vite/bin/vite.js build

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

# Copy built frontend assets
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Create directory for temporary files
RUN mkdir -p /tmp/invoices

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Run the API application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]

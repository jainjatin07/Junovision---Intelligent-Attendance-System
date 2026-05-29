# Use a slim Python base image
FROM python:3.10-slim

# Install system dependencies required for cmake, dlib, and OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    gfortran \
    git \
    wget \
    curl \
    graphicsmagick \
    libgraphicsmagick1-dev \
    libatlas-base-dev \
    libavcodec-dev \
    libavformat-dev \
    libgtk2.0-dev \
    libjpeg-dev \
    liblapack-dev \
    libswscale-dev \
    pkg-config \
    python3-dev \
    python3-numpy \
    libpng-dev \
    libtiff-dev \
    libjasper-dev \
    libx11-dev \
    libatlas-base-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency file first to leverage Docker caching
COPY requirements.txt .

# Install dependencies (dlib is pre-compiled using cmake installed above)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 5000 for Flask
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV PORT=5000

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

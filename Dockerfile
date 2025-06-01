# Use Python 3.13 slim image for smaller size
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash riko && \
    chown -R riko:riko /app
USER riko

# Expose port (not needed for Discord bot but good practice)
EXPOSE 8858

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import psutil; [p for p in psutil.process_iter() if 'python' in p.name().lower() and 'bot.py' in ' '.join(p.cmdline())]" || exit 1

# Run the bot
CMD ["python", "bot.py"] 
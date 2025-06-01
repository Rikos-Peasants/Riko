#!/bin/bash

# Riko Discord Bot - Docker Startup Script

echo "🤖 Starting Riko Discord Bot with Docker..."
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your bot configuration."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found!"
    echo "Please install docker-compose first."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo "📦 Building and starting the bot container..."

# Build and start the bot
docker-compose up --build -d

echo "✅ Bot container started!"
echo ""
echo "📋 Useful commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop bot:      docker-compose down"
echo "   Restart bot:   docker-compose restart"
echo "   Status:        docker-compose ps"
echo ""
echo "🔗 The bot should now be online in Discord!"
echo "   Text commands: R!uptime"
echo "   Slash commands: /uptime"

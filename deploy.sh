#!/bin/bash

# GoldMineAI Deployment Script
# This script builds and deploys the application using Docker

set -e  # Exit on any error

echo "🚀 Starting GoldMineAI deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose is not installed. Please install it and try again.${NC}"
    exit 1
fi

# Environment variables
export SECRET_KEY=${SECRET_KEY:-"your-secret-key-change-this-in-production"}
export DB_NAME=${DB_NAME:-"goldmineai"}
export DB_USER=${DB_USER:-"postgres"}
export DB_PASSWORD=${DB_PASSWORD:-"postgres"}
export DB_HOST=${DB_HOST:-"localhost"}
export DB_PORT=${DB_PORT:-"5432"}
export ALLOWED_HOSTS=${ALLOWED_HOSTS:-"localhost,127.0.0.1"}

echo -e "${YELLOW}📋 Environment Configuration:${NC}"
echo "   Database: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "   Allowed Hosts: ${ALLOWED_HOSTS}"
echo "   Secret Key: ${SECRET_KEY:0:20}..."

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down --remove-orphans

# Build the application
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker-compose build --no-cache

# Start the services
echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Check if the application is running
echo -e "${YELLOW}🔍 Checking application health...${NC}"
for i in {1..30}; do
    if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is healthy!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Application failed to start within 30 seconds${NC}"
        docker-compose logs web
        exit 1
    fi
    echo -n "."
    sleep 1
done

# Run database migrations
echo -e "${YELLOW}🗄️  Running database migrations...${NC}"
docker-compose exec web python manage.py migrate --noinput

# Collect static files
echo -e "${YELLOW}📁 Collecting static files...${NC}"
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser if needed
echo -e "${YELLOW}👤 Creating superuser (if needed)...${NC}"
echo "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | docker-compose exec -T web python manage.py shell

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${GREEN}📱 Application URLs:${NC}"
echo "   Main App: http://localhost:8000"
echo "   Maps: http://localhost:8000/maps/"
echo "   Admin: http://localhost:8000/admin/"
echo ""
echo -e "${GREEN}🔑 Default Admin Credentials:${NC}"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo -e "${YELLOW}⚠️  Remember to change the default admin password!${NC}"
echo ""
echo -e "${GREEN}📊 Container Status:${NC}"
docker-compose ps

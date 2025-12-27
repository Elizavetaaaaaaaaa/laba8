#!/bin/bash
# Скрипт быстрого запуска гибридного хранилища

echo "=========================================="
echo "  Hybrid Storage - Quick Start"
echo "=========================================="
echo ""

echo "1. Starting infrastructure..."
docker-compose up -d

echo ""
echo "2. Waiting for services to be ready..."
sleep 10

echo ""
echo "3. Checking status..."
docker-compose ps

echo ""
echo "=========================================="
echo "  Ready!"
echo "=========================================="
echo ""
echo "MinIO Console: http://localhost:9001"
echo "  Login: minioadmin"
echo "  Password: minioadmin123"
echo ""
echo "To start CLI application:"
echo "  docker-compose run --rm app"
echo ""
echo "To stop:"
echo "  docker-compose down"
echo ""

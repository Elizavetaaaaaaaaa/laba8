#!/bin/bash
set -e

echo "=========================================="
echo "  MinIO + s3fs Setup"
echo "=========================================="

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed!"
    exit 1
fi

echo "Starting MinIO..."
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

echo "Waiting for MinIO..."
sleep 15

if curl -s http://localhost:9000/minio/health/live > /dev/null; then
    echo "✓ MinIO is running"
else
    echo "❌ MinIO not accessible"
    exit 1
fi

echo ""
echo "=========================================="
echo "  MinIO Started!"
echo "=========================================="
echo ""
echo "📊 Web Console: http://localhost:9001"
echo "   Login: minioadmin / minioadmin"
echo ""
echo "🔌 S3 API: http://localhost:9000"
echo ""

if command -v s3fs &> /dev/null; then
    echo "Setting up s3fs..."
    PASSWD_FILE="$HOME/.passwd-s3fs"
    echo "minioadmin:minioadmin" > "$PASSWD_FILE"
    chmod 600 "$PASSWD_FILE"
    
    MOUNT_POINT="/tmp/minio_s3fs"
    mkdir -p "$MOUNT_POINT"
    
    if s3fs testbucket "$MOUNT_POINT" \
        -o url=http://localhost:9000 \
        -o use_path_request_style \
        -o passwd_file="$PASSWD_FILE" \
        -o allow_other 2>/dev/null; then
        echo "✓ s3fs mounted at $MOUNT_POINT"
        echo "test" > "$MOUNT_POINT/test.txt"
        cat "$MOUNT_POINT/test.txt"
    else
        echo "⚠️  s3fs mount failed (may need sudo)"
    fi
else
    echo "⚠️  s3fs not installed"
fi

echo ""
echo "Next steps:"
echo "  cd ../task2_benchmark"
echo "  python3 benchmark.py testbucket http://localhost:9000"

#!/bin/bash

echo "Stopping MinIO..."

MOUNT_POINT="/tmp/minio_s3fs"
if mount | grep -q "$MOUNT_POINT"; then
    fusermount -u "$MOUNT_POINT" 2>/dev/null || fusermount3 -u "$MOUNT_POINT" 2>/dev/null
    echo "✓ s3fs unmounted"
fi

if docker compose version &> /dev/null; then
    docker compose down
else
    docker-compose down
fi

echo "✓ MinIO stopped"

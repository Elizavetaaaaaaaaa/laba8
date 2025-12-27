#!/bin/bash

S3FS_MOUNT="/tmp/s3fs_mount"
GOOFYS_MOUNT="/tmp/goofys_mount"

echo "=== Unmounting S3 filesystems ==="

if mount | grep -q "$S3FS_MOUNT"; then
    fusermount -u "$S3FS_MOUNT" || fusermount3 -u "$S3FS_MOUNT"
    echo "✓ s3fs unmounted"
fi

if mount | grep -q "$GOOFYS_MOUNT"; then
    fusermount -u "$GOOFYS_MOUNT" || fusermount3 -u "$GOOFYS_MOUNT"
    echo "✓ goofys unmounted"
fi

echo "Done!"

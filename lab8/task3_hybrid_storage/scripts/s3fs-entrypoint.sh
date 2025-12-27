#!/bin/bash
set -e

# Создание файла credentials
echo "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" > /etc/passwd-s3fs
chmod 600 /etc/passwd-s3fs

# Ожидание готовности MinIO
echo "Waiting for MinIO to be ready..."
until curl -sf "${S3_ENDPOINT}/minio/health/live"; do
    echo 'MinIO not ready yet, waiting...'
    sleep 2
done
echo "MinIO is ready!"

# Создание bucket если не существует
echo "Creating bucket ${S3_BUCKET}..."
curl -X PUT "${S3_ENDPOINT}/${S3_BUCKET}" \
    -H "Host: ${S3_BUCKET}.localhost:9000" \
    --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" || true

# Создание mount point
mkdir -p /mnt/s3

# Монтирование
echo "Mounting S3 bucket..."
s3fs ${S3_BUCKET} /mnt/s3 \
    -o passwd_file=/etc/passwd-s3fs \
    -o url=${S3_ENDPOINT} \
    -o use_path_request_style \
    -o allow_other \
    -o parallel_count=15 \
    -o multipart_size=52

echo "S3FS mounted successfully at /mnt/s3"

# Держим контейнер запущенным
tail -f /dev/null

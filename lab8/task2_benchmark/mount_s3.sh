#!/bin/bash

# Останавливать скрипт при ошибках
set -e

BUCKET_NAME="${1:-testbucket}"
S3_ENDPOINT="${2:-http://localhost:9000}"
ACCESS_KEY="${AWS_ACCESS_KEY_ID:-minioadmin}"
SECRET_KEY="${AWS_SECRET_ACCESS_KEY:-minioadmin}"

S3FS_MOUNT="/tmp/s3fs"
GOOFYS_MOUNT="/tmp/goofys"
PASSWD_FILE="$HOME/.passwd-s3fs"

echo "=== Проверка окружения ==="

# 1. Проверка наличия утилит
for cmd in s3fs goofys; do
    if ! command -v $cmd &> /dev/null; then
        echo "Ошибка: утилита $cmd не установлена."
        exit 1
    fi
done

# 2. Очистка предыдущих маунтов (чтобы избежать "Transport endpoint is not connected")
cleanup() {
    echo "Очистка старых точек монтирования..."
    fusermount -u "$S3FS_MOUNT" 2>/dev/null || true
    fusermount -u "$GOOFYS_MOUNT" 2>/dev/null || true
    mkdir -p "$S3FS_MOUNT" "$GOOFYS_MOUNT"
}
cleanup

# 3. Настройка учетных данных для s3fs
echo "$ACCESS_KEY:$SECRET_KEY" > "$PASSWD_FILE"
chmod 600 "$PASSWD_FILE"

echo "=== Монтирование S3 bucket: $BUCKET_NAME ==="

# 4. Монтирование s3fs
# Добавлен флаг -o dbglevel=info для логов при ошибках (можно убрать).
echo "Запуск s3fs..."
s3fs "$BUCKET_NAME" "$S3FS_MOUNT" \
    -o url="$S3_ENDPOINT" \
    -o use_path_request_style \
    -o passwd_file="$PASSWD_FILE" \
    -o allow_other \
    -o nonempty

# 5. Монтирование goofys
# Goofys требует переменные окружения или конфиг.
export AWS_ACCESS_KEY_ID="$ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$SECRET_KEY"

echo "Запуск goofys..."
# Мы просто убираем проблемный флаг. Goofys сам поймет, как работать с localhost
goofys --debug_s3 --endpoint="$S3_ENDPOINT" "$BUCKET_NAME" "$GOOFYS_MOUNT"

# 6. Проверка результата
sleep 1
echo "=== Результат ==="
if mountpoint -q "$S3FS_MOUNT"; then echo "✅ s3fs: Смонтировано в $S3FS_MOUNT"; else echo "❌ s3fs: Ошибка"; fi
if mountpoint -q "$GOOFYS_MOUNT"; then echo "✅ goofys: Смонтировано в $GOOFYS_MOUNT"; else echo "❌ goofys: Ошибка"; fi
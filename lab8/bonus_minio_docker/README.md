# Бонус: MinIO + s3fs в Docker

## Быстрый старт

```bash
./start.sh
```

## Доступ

- Web Console: http://localhost:9001 (minioadmin/minioadmin)
- S3 API: http://localhost:9000

## Остановка

```bash
./stop.sh
```

## Использование с AWS CLI

```bash
aws --endpoint-url http://localhost:9000 s3 ls
aws --endpoint-url http://localhost:9000 s3 cp file.txt s3://testbucket/
```

## Монтирование s3fs

```bash
s3fs testbucket /tmp/mount \
  -o url=http://localhost:9000 \
  -o use_path_request_style \
  -o passwd_file=~/.passwd-s3fs
```

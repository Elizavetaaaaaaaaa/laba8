# Лабораторная работа №8: Файловые системы

## Выполненные задания

✅ **Задание 1:** FUSE SQLite файловая система (C)
✅ **Задание 2:** Benchmark s3fs vs goofys vs native S3 (Python)  
✅ **Задание 3:** Архитектура hybrid filesystem
✅ **Бонус:** MinIO + s3fs в Docker

## Структура

```
laba8/
├── task1_fuse_sqlite/       # FUSE ФС с SQLite
│   ├── fuse_sqlite_fs.c
│   ├── Makefile
│   └── README.md
│
├── task2_benchmark/         # Бенчмарки S3
│   ├── benchmark.py
│   ├── mount_s3.sh
│   ├── umount_s3.sh
│   └── README.md
│
├── task3_architecture/      # Архитектура
│   ├── hybrid_filesystem_design.md
│   └── generate_diagrams.py
│
└── bonus_minio_docker/      # MinIO Docker
    ├── docker-compose.yml
    ├── start.sh
    ├── stop.sh
    └── README.md
```

## Быстрый старт

### 1. FUSE SQLite ФС
```bash
cd task1_fuse_sqlite/
make
mkdir mountpoint
./fuse_sqlite_fs mountpoint -f
```

### 2. MinIO (запустить сначала!)
```bash
cd bonus_minio_docker/
./start.sh
# Web Console: http://localhost:9001 (minioadmin/minioadmin)
```

### 3. Бенчмарки
```bash
cd task2_benchmark/
./mount_s3.sh testbucket http://localhost:9000
python3 benchmark.py testbucket http://localhost:9000
```

### 4. Архитектура
```bash
cd task3_architecture/
python3 generate_diagrams.py
```

## Зависимости

```bash
# FUSE + SQLite
sudo apt-get install libfuse3-dev libsqlite3-dev build-essential

# S3 tools
sudo apt-get install s3fs awscli
wget https://github.com/kahing/goofys/releases/latest/download/goofys
chmod +x goofys && sudo mv goofys /usr/local/bin/

# Python
pip3 install matplotlib pandas numpy boto3

# Docker
sudo apt-get install docker.io docker-compose
```

## Что реализовано

### Задание 1: FUSE SQLite ФС
- ✅ Полная FUSE реализация на C
- ✅ SQLite для хранения метаданных и данных
- ✅ read, write, mkdir, rmdir, create, unlink
- ✅ Makefile для сборки

### Задание 2: Benchmark
- ✅ Python скрипт для бенчмарков
- ✅ Sequential, Random, Small Files workloads
- ✅ Графики matplotlib
- ✅ JSON и текстовый отчеты

### Задание 3: Архитектура  
- ✅ Трехуровневая система (Hot/Warm/Cold)
- ✅ Multi-DC репликация
- ✅ Auto-tiering политики
- ✅ TCO анализ ($3.39M за 5 лет)
- ✅ Диаграммы

### Бонус: MinIO
- ✅ Docker Compose конфигурация
- ✅ Автоматическое создание buckets
- ✅ Интеграция с s3fs
- ✅ Web Console

## Troubleshooting

### FUSE права
```bash
sudo usermod -a -G fuse $USER
newgrp fuse
```

### s3fs не монтируется
```bash
cat ~/.passwd-s3fs  # Должно быть: minioadmin:minioadmin
chmod 600 ~/.passwd-s3fs
```

### Docker порты заняты
Измените порты в `docker-compose.yml`

## Документация

Каждое задание имеет свой README с детальными инструкциями.

# Задание 2: Benchmark сравнение S3 решений

## Описание

Сравнительный анализ производительности различных способов работы с S3-совместимым хранилищем:
- **s3fs** - FUSE драйвер (C++)
- **goofys** - FUSE драйвер (Go) 
- **Native S3 API** - boto3 (Python)

## Структура проекта

```
task2_benchmark/
├── benchmark/              # Модульный framework
│   ├── __init__.py
│   ├── base.py            # Базовый класс BenchmarkBase
│   ├── filesystem.py      # Бенчмарки для FUSE ФС
│   ├── native_s3.py       # Бенчмарки для boto3
│   ├── workloads.py       # Определения нагрузок
│   ├── metrics.py         # Сбор и расчёт метрик
│   └── visualize.py       # Генерация графиков
├── main.py                # Точка входа
├── mount_s3.sh            # Скрипт монтирования
├── umount_s3.sh           # Скрипт размонтирования
└── README_FULL.md         # Эта инструкция
```

## Установка зависимостей

### Python пакеты
```bash
pip install boto3 matplotlib numpy
```

### s3fs-fuse
```bash
sudo apt-get update
sudo apt-get install -y s3fs
```

### goofys
```bash
wget https://github.com/kahing/goofys/releases/download/v0.24.0/goofys
chmod +x goofys
sudo mv goofys /usr/local/bin/
```

### Создание директорий для монтирования
```bash
sudo mkdir -p /tmp/s3fs /tmp/goofys
sudo chown $USER:$USER /tmp/s3fs /tmp/goofys
```

## Подготовка тестового окружения

### Запуск MinIO (локальный S3)

```bash
# Скачивание MinIO сервера
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio

# Запуск сервера (в отдельном терминале)
MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin123 \
  ./minio server /tmp/minio-data --address :9000 --console-address :9001
```

Создание bucket:
```bash
# Скачивание MinIO Client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc

# Настройка и создание bucket
./mc alias set local http://localhost:9000 minioadmin minioadmin123
./mc mb local/benchmark
```

### Настройка credentials для s3fs

```bash
echo 'minioadmin:minioadmin123' > ~/.passwd-s3fs
chmod 600 ~/.passwd-s3fs
```

### Монтирование файловых систем

**s3fs:**
```bash
s3fs benchmark /tmp/s3fs \
    -o passwd_file=~/.passwd-s3fs \
    -o url=http://localhost:9000 \
    -o use_path_request_style
```

**goofys:**
```bash
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin123
goofys --endpoint http://localhost:9000 benchmark /tmp/goofys
```

Или используйте готовый скрипт:
```bash
./mount_s3.sh benchmark http://localhost:9000
```

## Запуск бенчмарков

### Только Native S3 API (быстрый старт)

```bash
python3 main.py \
    --bucket benchmark \
    --endpoint http://localhost:9000 \
    --storage native_s3
```

### Все типы хранилищ

```bash
python3 main.py \
    --bucket benchmark \
    --endpoint http://localhost:9000 \
    --storage s3fs goofys native_s3 \
    --s3fs-mount /tmp/s3fs \
    --goofys-mount /tmp/goofys
```

### Конкретные нагрузки

```bash
python3 main.py \
    --bucket benchmark \
    --endpoint http://localhost:9000 \
    --storage native_s3 \
    --workloads sequential_write sequential_read random_io
```

### Изменение количества итераций

```bash
python3 main.py \
    --bucket benchmark \
    --endpoint http://localhost:9000 \
    --storage native_s3 \
    --iterations 50  # меньше итераций = быстрее
```

## Типы нагрузок

| Workload | Параметры | Что измеряет |
|----------|-----------|--------------|
| **sequential_write** | 1 MB × 100 файлов | Throughput записи больших файлов |
| **sequential_read** | 1 MB × 100 файлов | Throughput чтения больших файлов |
| **random_io** | 4 KB блоки, случайные | IOPS при случайном доступе |
| **small_files** | 4 KB × 1000 файлов | Overhead на создание мелких файлов |
| **metadata_ops** | stat/create/delete | Latency операций с метаданными |

## Собираемые метрики

- **Throughput** (MB/s) - пропускная способность
- **IOPS** - операций в секунду
- **Latency** (ms):
  - Average - среднее
  - P95 - 95-й перцентиль
  - P99 - 99-й перцентиль

## Выходные файлы

После выполнения бенчмарка в `benchmark_results/` создаются:

1. **benchmark_raw_TIMESTAMP.json** - сырые данные (для воспроизводимости)
2. **benchmark_report_TIMESTAMP.txt** - текстовый отчёт с выводами
3. **01_throughput_comparison.png** - график пропускной способности
4. **02_iops_comparison.png** - график IOPS
5. **03_latency_percentiles.png** - распределение задержек
6. **04_performance_radar.png** - радарный график общей производительности

## Формат отчёта

Отчёт содержит:

1. **Введение** - цель исследования, тестируемые решения
2. **Методология** - параметры тестового стенда, нагрузок
3. **Результаты** - таблицы с метриками для каждой нагрузки
4. **Сравнение** - относительная производительность
5. **Рекомендации** - когда использовать каждое решение

## Пример вывода

```
================================================================================
S3 STORAGE BENCHMARK
================================================================================
Bucket:       benchmark
Endpoint:     http://localhost:9000
Storage:      native_s3, s3fs, goofys
Workloads:    sequential_write, sequential_read, random_io
Iterations:   100
Output:       benchmark_results
================================================================================

[1/9] Running native_s3 / sequential_write...
--------------------------------------------------------------------------------
[native_s3] Запуск sequential_write...
  Progress: 10/100
  Progress: 20/100
  ...
✅ Completed: 45.23 MB/s, 45.2 IOPS, 22.14ms avg latency

...

================================================================================
SAVING RESULTS
================================================================================
✅ Raw data saved: benchmark_results/benchmark_raw_20231220_153045.json

================================================================================
S3 STORAGE BENCHMARK REPORT
================================================================================
Timestamp: 20231220_153045

================================================================================
WORKLOAD: SEQUENTIAL_WRITE
================================================================================

  Storage: native_s3
  ──────────────────────────────────────────────────────────────────────
    Throughput:          45.23 MB/s
    IOPS:                45.20 ops/s
    Latency (avg):       22.14 ms
    Latency (p95):       35.67 ms
    Latency (p99):       42.89 ms
    Total time:          2.21 sec
    Errors:                  0

...

================================================================================
RECOMMENDATIONS
================================================================================

• sequential_write:
    Best: native_s3 (45.23 MB/s)
    → Good for: Large file transfers, backups, data lakes

...
```

## Размонтирование

```bash
./umount_s3.sh
```

Или вручную:
```bash
fusermount -u /tmp/s3fs
fusermount -u /tmp/goofys
```

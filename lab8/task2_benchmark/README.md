# Задание 2: Benchmark сравнение S3 решений

## Описание

Сравнительный анализ производительности различных способов работы с S3-совместимым хранилищем:
- **s3fs** - FUSE драйвер (C++)
- **goofys** - FUSE драйвер (Go) 
- **Native S3 API** - boto3 (Python)

## Быстрый старт (демо)

```bash
# Установка зависимостей
pip3 install numpy matplotlib boto3

# Запуск демо (без реального S3)
python3 demo.py
```

Результаты сохранятся в `benchmark_results_demo/`:
- 4 графика (throughput, IOPS, latency, radar chart)
- JSON с сырыми данными
- Текстовый отчёт с рекомендациями

## Запуск с реальным S3

### 1. Установка
```bash
pip3 install -r requirements.txt
sudo apt-get install s3fs
wget https://github.com/kahing/goofys/releases/download/v0.24.0/goofys
chmod +x goofys && sudo mv goofys /usr/local/bin/
```

### 2. Запуск MinIO
```bash
# Скачайте и запустите MinIO сервер
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server /tmp/minio-data --address :9000 --console-address :9001
```

### 3. Монтирование (опционально для s3fs/goofys)
```bash
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin123
./mount_s3.sh benchmark http://localhost:9000
```

### 4. Запуск бенчмарка
```bash
# Только Native S3 (быстро)
python3 main.py --bucket benchmark --endpoint http://localhost:9000 --storage native_s3

# Все типы хранилищ
python3 main.py --bucket benchmark --endpoint http://localhost:9000 \
    --storage s3fs goofys native_s3 \
    --s3fs-mount /mnt/s3fs --goofys-mount /mnt/goofys
```

## Типы нагрузок

- **sequential_write** - последовательная запись (1 MB × 100)
- **sequential_read** - последовательное чтение (1 MB × 100)
- **random_io** - случайный доступ (4 KB блоки)
- **small_files** - мелкие файлы (4 KB × 1000)
- **metadata_ops** - операции с метаданными

## Выходные файлы

В `benchmark_results/`:
1. `benchmark_raw_*.json` - сырые данные
2. `benchmark_report_*.txt` - отчёт с рекомендациями
3. `01_throughput_comparison.png`
4. `02_iops_comparison.png`
5. `03_latency_percentiles.png`
6. `04_performance_radar.png`

## Структура

```
task2_benchmark/
├── benchmark/         # Модульный framework
├── main.py           # Основной скрипт
├── demo.py           # Демо без S3
└── README_FULL.md    # Полная документация
```

## Полная документация

См. **README_FULL.md** для детальных инструкций.

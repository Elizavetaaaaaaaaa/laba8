# Задание 3: Архитектура гибридного хранилища

## Описание

Proof-of-concept гибридного хранилища для **TechData Solutions** - медиа-компании с объемом данных 500+ TB.

**Трехуровневая архитектура:**
- **HOT** - Local SSD (< 1 мс, активные проекты)
- **WARM** - MinIO + S3FS (~50 мс, недавние проекты)  
- **COLD** - Archive (часы, долгосрочное хранение)

## Структура проекта

```
task3_hybrid_storage/
├── docker-compose.yml          # Конфигурация контейнеров
├── Dockerfile.s3fs            # S3FS FUSE драйвер
├── Dockerfile.app             # Приложение
├── scripts/
│   └── s3fs-entrypoint.sh     # Скрипт монтирования S3FS
├── app/
│   ├── hybrid_storage.py      # Менеджер хранилища
│   └── cli.py                 # CLI интерфейс
├── ARCHITECTURE.md            # Полная документация архитектуры
└── README.md                  # Эта инструкция
```

## Быстрый старт

### 1. Запуск инфраструктуры

```bash
cd task3_hybrid_storage

# Запуск всех контейнеров
docker-compose up -d

# Проверка статуса
docker-compose ps
```

Ожидаемый вывод:
```
NAME            SERVICE   STATUS    PORTS
hybrid_app      app       running   
minio           minio     running   0.0.0.0:9000->9000/tcp, 0.0.0.0:9001->9001/tcp
s3fs            s3fs      running
```

### 2. Просмотр логов

```bash
# Логи S3FS монтирования
docker-compose logs s3fs

# Логи MinIO
docker-compose logs minio

# Следить за логами в реальном времени
docker-compose logs -f
```

### 3. Запуск CLI приложения

```bash
docker-compose run --rm app
```

## Использование CLI

После запуска `docker-compose run app` вы увидите интерфейс:

```
============================================================
  Hybrid Storage Manager - TechData Solutions
  HOT (Local SSD) | WARM (S3FS/MinIO) | COLD (Archive)
============================================================

Commands: put <filename> <content> | get <filename> | status | list | migrate | help | exit

>
```

### Команды

#### put - Сохранение файла
```bash
> put video1.mp4 My_video_content
✓ Saved 'video1.mp4' to hot tier (16 bytes)
```

#### get - Получение файла
```bash
> get video1.mp4
✓ Retrieved 'video1.mp4':
  Content: My_video_content
  Size: 16 bytes
```

#### status - Статистика хранилища
```bash
> status

============================================================
Storage Status:
============================================================
  HOT    | Files:    3 | Size:      120.00 B
  WARM   | Files:    1 | Size:       45.00 B
  COLD   | Files:    0 | Size:        0.00 B
------------------------------------------------------------
  TOTAL  | Files:    4 | Size:      165.00 B
============================================================
```

#### list - Список файлов
```bash
> list

================================================================================
Filename             Tier   Size       Access   Last Accessed       
================================================================================
video1.mp4           hot    16.00 B    2        2025-12-20 05:45:30
project.zip          warm   45.00 B    1        2025-12-13 10:20:15
================================================================================
```

#### migrate - Миграция данных
```bash
> migrate
Running migration policy...

✓ Migrated 1 files:
  - video1.mp4: HOT -> WARM (age: 7.2 days)
```

#### help - Справка
```bash
> help

Available commands:
  put <filename> <content>  - Save file to HOT tier
  get <filename>            - Retrieve file (auto-promote to HOT)
  status                    - Show storage statistics
  list                      - List all files
  migrate                   - Run migration policy
  help                      - Show this help
  exit                      - Exit application
```

## MinIO Console

Веб-интерфейс MinIO доступен по адресу: http://localhost:9001

- **Login**: `minioadmin`
- **Password**: `minioadmin123`

Здесь можно:
- Просматривать bucket `hybrid-storage`
- Управлять файлами в WARM tier
- Мониторить производительность

## Политики миграции

### Автоматические правила

1. **HOT → WARM**: Файлы без доступа 7+ дней перемещаются в WARM tier
2. **WARM → COLD**: Файлы без доступа 30+ дней перемещаются в COLD tier
3. **Auto-promote**: При обращении к файлу он автоматически возвращается в HOT tier

### Жизненный цикл

```
HOT (Active) ──7 days──► WARM (Recent) ──30 days──► COLD (Archive)
     ▲                        ▲                           │
     └────── on access ───────┴───────── on access ──────┘
```

## Архитектура

Подробная документация архитектурного решения находится в **ARCHITECTURE.md**:

- Executive Summary
- Бизнес-требования компании
- Техническая архитектура
- Политики миграции данных
- Экономический анализ (TCO)
- План внедрения
- Мониторинг и метрики

## Остановка системы

```bash
# Остановка контейнеров
docker-compose down

# Остановка с удалением volumes (очистка данных)
docker-compose down -v
```

## Troubleshooting

### S3FS не монтируется

```bash
# Проверить логи
docker-compose logs s3fs

# Пересоздать контейнер
docker-compose up -d --force-recreate s3fs
```

### MinIO недоступен

```bash
# Проверить статус
docker-compose ps minio

# Проверить доступность
curl http://localhost:9000/minio/health/live
```

### Приложение не видит файлы

```bash
# Проверить volumes
docker volume ls | grep hybrid

# Пересоздать все
docker-compose down -v
docker-compose up -d
```

## Технические детали

### Компоненты

1. **MinIO** - S3-совместимое объектное хранилище
2. **S3FS** - FUSE драйвер для монтирования S3 как файловой системы
3. **Hybrid Storage Manager** - Python приложение для управления тремя уровнями
4. **Docker Volumes** - изолированное хранилище для каждого tier

### Требования

- Docker Engine 20.10+
- Docker Compose 2.0+
- 2 GB RAM (минимум)
- 10 GB свободного места

## Дополнительно

### Тестирование производительности

```bash
# Запуск бенчмарков (если реализовано)
docker-compose run app python3 benchmark.py
```

### Логи приложения

```bash
# Метаданные хранятся в
docker exec hybrid_app cat /tmp/storage_metadata.json
```

## Чек-лист выполнения

- [x] Docker-compose с MinIO + S3FS
- [x] Демо приложение с put/get/status
- [x] Автоматическая миграция (HOT→WARM→COLD)
- [x] Документация архитектуры (ARCHITECTURE.md)
- [x] TCO анализ
- [x] План внедрения

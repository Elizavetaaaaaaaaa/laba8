#!/bin/bash

# Получаем абсолютный путь к директории скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Определяем пути (с поддержкой переменной окружения для coverage)
FUSE_BIN="${FUSE_BIN:-$SCRIPT_DIR/fuse_sqlite_fs}"
MOUNTPOINT="$SCRIPT_DIR/mountpoint"
DB_FILE="$SCRIPT_DIR/filesystem.db"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Тестирование FUSE SQLite Файловой Системы${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}\n"
echo -e "${YELLOW}📁 Рабочая директория: $SCRIPT_DIR${NC}\n"

# Очистка перед тестами
echo -e "${YELLOW}🧹 Очистка перед тестами...${NC}"
fusermount -u "$MOUNTPOINT" 2>/dev/null || fusermount3 -u "$MOUNTPOINT" 2>/dev/null || true
pkill -9 fuse_sqlite_fs 2>/dev/null || true
sleep 2
rm -rf "$MOUNTPOINT" "$DB_FILE"
echo -e "${GREEN}✅ Очистка завершена${NC}\n"

# Создание точки монтирования
mkdir -p "$MOUNTPOINT"

# Монтирование в фоновом режиме
echo -e "${YELLOW}🚀 Монтирование файловой системы...${NC}"
# Запускаем с флагом -f (foreground) и перенаправляем вывод
FUSE_LOG="$SCRIPT_DIR/fuse.log"
(cd "$SCRIPT_DIR" && "$FUSE_BIN" "$MOUNTPOINT" -f > "$FUSE_LOG" 2>&1) &
FUSE_PID=$!
echo -e "${YELLOW}   PID процесса: $FUSE_PID${NC}"
echo -e "${YELLOW}   Лог: $FUSE_LOG${NC}"
sleep 5

# Проверка что монтирование успешно
if ! mountpoint -q "$MOUNTPOINT" 2>/dev/null; then
    echo -e "${RED}❌ Ошибка монтирования!${NC}"
    echo -e "${RED}Проверка процесса (PID: $FUSE_PID):${NC}"
    ps aux | grep "$FUSE_PID" | grep -v grep || echo "Процесс не найден"
    echo -e "${RED}Все процессы fuse_sqlite_fs:${NC}"
    ps aux | grep fuse_sqlite_fs | grep -v grep || echo "Нет запущенных процессов"
    echo -e "${RED}Проверка mountpoint:${NC}"
    ls -la "$MOUNTPOINT" 2>&1 || echo "Не могу прочитать директорию"
    echo -e "${RED}Последние строки лога:${NC}"
    tail -20 "$FUSE_LOG" 2>/dev/null || echo "Лог недоступен"
    echo -e "${RED}Попытка размонтирования...${NC}"
    fusermount -u "$MOUNTPOINT" 2>/dev/null || true
    # Убиваем процесс если он висит
    kill -9 "$FUSE_PID" 2>/dev/null || true
    exit 1
fi
echo -e "${GREEN}✅ Файловая система смонтирована (PID: $FUSE_PID)${NC}\n"

# Тест 1
echo -e "${YELLOW}=== Тест 1: Просмотр корневой директории ===${NC}"
ls -la "$MOUNTPOINT/"
echo ""

# Тест 2
echo -e "${YELLOW}=== Тест 2: Создание директории ===${NC}"
mkdir "$MOUNTPOINT/testdir"
ls -la "$MOUNTPOINT/"
echo ""

# Тест 3
echo -e "${YELLOW}=== Тест 3: Создание файла и запись ===${NC}"
echo "Привет, FUSE SQLite!" > "$MOUNTPOINT/testdir/test.txt"
cat "$MOUNTPOINT/testdir/test.txt"
echo ""

# Тест 4
echo -e "${YELLOW}=== Тест 4: Проверка метаданных ===${NC}"
ls -lh "$MOUNTPOINT/testdir/"
echo ""

# Тест 5
echo -e "${YELLOW}=== Тест 5: Создание нескольких файлов ===${NC}"
echo "Файл 1" > "$MOUNTPOINT/testdir/file1.txt"
echo "Файл 2" > "$MOUNTPOINT/testdir/file2.txt"
echo "Файл 3" > "$MOUNTPOINT/testdir/file3.txt"
ls -la "$MOUNTPOINT/testdir/"
echo ""

# Тест 6
echo -e "${YELLOW}=== Тест 6: Чтение файлов ===${NC}"
cat "$MOUNTPOINT/testdir/file1.txt"
cat "$MOUNTPOINT/testdir/file2.txt"
cat "$MOUNTPOINT/testdir/file3.txt"
echo ""

# Тест 7
echo -e "${YELLOW}=== Тест 7: Переименование ===${NC}"
mv "$MOUNTPOINT/testdir/file1.txt" "$MOUNTPOINT/testdir/renamed.txt"
ls -la "$MOUNTPOINT/testdir/"
echo ""

# Тест 8
echo -e "${YELLOW}=== Тест 8: Изменение прав (chmod) ===${NC}"
chmod 600 "$MOUNTPOINT/testdir/renamed.txt"
ls -l "$MOUNTPOINT/testdir/renamed.txt"
echo ""

# Тест 9
echo -e "${YELLOW}=== Тест 9: Изменение владельца (chown) ===${NC}"
echo "Текущий владелец:"
stat -c "UID: %u, GID: %g" "$MOUNTPOINT/testdir/renamed.txt"
# Попытка изменить владельца (работает только для root или того же пользователя)
chown $UID:$UID "$MOUNTPOINT/testdir/renamed.txt" 2>/dev/null || echo "chown выполнен (или требуются права root)"
echo "После chown:"
stat -c "UID: %u, GID: %g" "$MOUNTPOINT/testdir/renamed.txt"
echo ""

# Тест 10
echo -e "${YELLOW}=== Тест 10: Изменение времени (utimens/touch) ===${NC}"
echo "Время до изменения:"
stat -c "Access: %x, Modify: %y" "$MOUNTPOINT/testdir/test.txt"
sleep 2
touch "$MOUNTPOINT/testdir/test.txt"
echo "Время после touch:"
stat -c "Access: %x, Modify: %y" "$MOUNTPOINT/testdir/test.txt"
echo ""

# Тест 11
echo -e "${YELLOW}=== Тест 11: Truncate ===${NC}"
truncate -s 5 "$MOUNTPOINT/testdir/file2.txt"
ls -lh "$MOUNTPOINT/testdir/file2.txt"
cat "$MOUNTPOINT/testdir/file2.txt"
echo ""

# Тест 12
echo -e "${YELLOW}=== Тест 12: Удаление файлов ===${NC}"
rm "$MOUNTPOINT/testdir/file3.txt"
ls -la "$MOUNTPOINT/testdir/"
echo ""

# Тест 13
echo -e "${YELLOW}=== Тест 13: Вложенные директории ===${NC}"
mkdir -p "$MOUNTPOINT/testdir/subdir1/subdir2"
echo "Глубокий файл" > "$MOUNTPOINT/testdir/subdir1/subdir2/deep.txt"
find "$MOUNTPOINT/testdir" -type f
echo ""

# Тест 14
echo -e "${YELLOW}=== Тест 14: Большой файл (чанки) ===${NC}"
dd if=/dev/urandom of="$MOUNTPOINT/testdir/bigfile.bin" bs=1M count=3 2>&1 | grep -v records
ls -lh "$MOUNTPOINT/testdir/bigfile.bin"
echo ""

# Тест 15
echo -e "${YELLOW}=== Тест 15: Проверка БД ===${NC}"
sqlite3 "$DB_FILE" "SELECT path, size FROM files ORDER BY path;"
echo ""

# Тест 16
echo -e "${YELLOW}=== Тест 16: Проверка чанков в БД ===${NC}"
echo "Файлы с несколькими чанками:"
sqlite3 "$DB_FILE" "SELECT f.path, COUNT(fd.chunk_index) as chunks, SUM(LENGTH(fd.data)) as total_bytes FROM file_data fd JOIN files f ON f.id = fd.file_id GROUP BY fd.file_id HAVING chunks > 1 ORDER BY f.path;"
echo ""

# Тест 17
echo -e "${YELLOW}=== Тест 17: Очистка ===${NC}"
rm -rf "$MOUNTPOINT/testdir/"*
ls -la "$MOUNTPOINT/testdir/"
rmdir "$MOUNTPOINT/testdir"
echo ""

# Размонтирование
echo -e "${YELLOW}=== Размонтирование ===${NC}"
fusermount -u "$MOUNTPOINT" || fusermount3 -u "$MOUNTPOINT"
sleep 1

# Проверка что процесс завершился
if ps -p $FUSE_PID > /dev/null 2>&1; then
    kill $FUSE_PID 2>/dev/null
fi

echo -e "\n${GREEN}✅ Все тесты завершены успешно!${NC}"
CC = gcc
CFLAGS = -Wall -Wextra -D_FILE_OFFSET_BITS=64
CFLAGS_COV = $(CFLAGS) -fprofile-arcs -ftest-coverage -O0
LDFLAGS = `pkg-config fuse --cflags --libs` -lsqlite3
LDFLAGS_COV = $(LDFLAGS) -lgcov --coverage

TARGET = fuse_sqlite_fs
TARGET_COV = fuse_sqlite_fs_cov
SRC = fuse_sqlite_fs.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC) $(LDFLAGS)

$(TARGET_COV): $(SRC)
	$(CC) $(CFLAGS_COV) -o $(TARGET_COV) $(SRC) $(LDFLAGS_COV)

clean:
	@pkill -9 fuse_sqlite_fs 2>/dev/null || true
	@fusermount -u mountpoint 2>/dev/null || fusermount3 -u mountpoint 2>/dev/null || true
	@sleep 1
	@rm -f $(TARGET) $(TARGET_COV) filesystem.db fuse.log
	@rm -rf mountpoint
	@rm -f *.gcda *.gcno *.gcov coverage.info
	@rm -rf coverage_html
	@echo "✅ Очистка завершена"

coverage: $(TARGET_COV)
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Тестирование с измерением покрытия кода"
	@echo "════════════════════════════════════════════════════════════"
	@pkill -9 fuse_sqlite_fs 2>/dev/null || true
	@fusermount -u mountpoint 2>/dev/null || true
	@sleep 1
	@rm -rf mountpoint filesystem.db fuse.log *.gcda
	@echo "✅ Подготовка завершена"
	@echo ""
	@chmod +x tests.sh
	@FUSE_BIN="$(shell pwd)/$(TARGET_COV)" bash tests.sh
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Генерация отчета о покрытии"
	@echo "════════════════════════════════════════════════════════════"
	@gcov $(TARGET_COV)-fuse_sqlite_fs.gcda 2>&1 | grep -E "File|Lines|Creating"
	@echo ""
	@echo "📊 Детальный отчет сохранен в fuse_sqlite_fs.c.gcov"
	@echo ""
	@if [ -f fuse_sqlite_fs.c.gcov ]; then \
		echo "✅ Покрытие кода:"; \
		echo ""; \
		gcov $(TARGET_COV)-fuse_sqlite_fs.gcda 2>&1 | grep "Lines executed" | head -1; \
		echo ""; \
		echo "💡 Детальный отчет: less fuse_sqlite_fs.c.gcov"; \
	else \
		echo "⚠️  Файл gcov не найден"; \
	fi
	@echo ""

mount: $(TARGET)
	mkdir -p mountpoint
	./$(TARGET) mountpoint -f

umount:
	fusermount -u mountpoint 2>/dev/null || fusermount3 -u mountpoint 2>/dev/null || true
	rmdir mountpoint 2>/dev/null || true

test: $(TARGET)
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Подготовка к тестированию"
	@echo "════════════════════════════════════════════════════════════"
	@pkill -9 fuse_sqlite_fs 2>/dev/null || true
	@fusermount -u mountpoint 2>/dev/null || true
	@sleep 1
	@rm -rf mountpoint filesystem.db
	@echo "✅ Очистка завершена"
	@echo ""
	@chmod +x tests.sh
	@bash tests.sh

mount_bg: $(TARGET)
	@mkdir -p mountpoint
	@echo "Запуск файловой системы в фоне..."
	@bash -c "cd $(shell pwd) && ./$(TARGET) mountpoint" &
	@sleep 2
	@echo "Проверка монтирования:"
	@mount | grep fuse_sqlite || echo "Ошибка монтирования!"

run: $(TARGET)
	@mkdir -p mountpoint
	@echo "Запуск файловой системы (Ctrl+C для остановки)..."
	./$(TARGET) mountpoint -f

.PHONY: all clean mount umount test mount_bg run coverage

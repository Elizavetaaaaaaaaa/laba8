# Задание 1: FUSE SQLite Файловая Система

## Установка зависимостей

```bash
sudo apt update
sudo apt install -y libfuse-dev libfuse3-dev libsqlite3-dev pkg-config build-essential
```

## Сборка

```bash
make
```

## Использование

### Монтирование:
```bash
mkdir -p mountpoint
./fuse_sqlite_fs mountpoint -f
```

### Тестирование:
```bash
mkdir mountpoint/mydir
echo "test" > mountpoint/mydir/file.txt
cat mountpoint/mydir/file.txt
ls -la mountpoint/mydir/
rm mountpoint/mydir/file.txt
rmdir mountpoint/mydir
```

### Размонтирование:
```bash
fusermount -u mountpoint
```

## Поддерживаемые операции

- ✅ mkdir, rmdir
- ✅ create, read, write, unlink
- ✅ getattr, readdir
- ✅ truncate
### Покрытие:
```bash
gcov fuse_sqlite_fs.c 2>&1 | head -30
gcov fuse_sqlite_fs.c -o . 2>&1 | head -50
gcov fuse_sqlite_fs_cov-fuse_sqlite_fs.gcda 2>&1 | grep -E "(File|Lines|Creating)" | head -20
# запуск
make clean && make coverage 2>&1 | tail -40
```
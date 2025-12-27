#define FUSE_USE_VERSION 26

#include <fuse.h>
#include <sqlite3.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdlib.h>
#include <time.h>
#include <sys/stat.h>
#include <unistd.h>
#include <sys/stat.h>

static sqlite3 *db = NULL;
#define DB_PATH "filesystem.db"

#define CHUNK_SIZE (1024 * 1024)    // 1 МБ

static int init_database(void) {
    int rc = sqlite3_open(DB_PATH, &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "НЕ ОТКРЫЛАСЬ БД: %s\n", sqlite3_errmsg(db));
        return -1;
    }

    // внешние ключи для автоудаления
    sqlite3_exec(db, "PRAGMA foreign_keys = ON;", NULL, NULL, NULL);

    const char *sql_files = 
        "CREATE TABLE IF NOT EXISTS files ("
        "    id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "    path TEXT UNIQUE NOT NULL,"        // Полный путь
        "    mode INTEGER NOT NULL,"            // Права доступа    (S_IFREG, S_IFDIR)
        "    uid INTEGER NOT NULL,"             // ID владельца     (getuid())
        "    gid INTEGER NOT NULL,"             // ID группы        (getgid())
        "    size INTEGER DEFAULT 0,"           // Размер файла
        "    atime REAL NOT NULL,"              // Время последнего доступа
        "    mtime REAL NOT NULL,"              // Время последней модификации
        "    ctime REAL NOT NULL,"              // Время последнего изменения статуса
        "    nlink INTEGER DEFAULT 1"           // Количество жестких ссылок    
        ");";

        
    const char *sql_data = 
        "CREATE TABLE IF NOT EXISTS file_data ("
        "   id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "   file_id INTEGER NOT NULL,"   // ссылка на files.id
        "   chunk_index INTEGER NOT NULL,"
        "   data BLOB,"
        "   FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,"
        "   UNIQUE(file_id, chunk_index)"   // Один чанк = одна запись
        ");";

    // индексы
    const char *sql_indexes =
        "CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);"
        "CREATE INDEX IF NOT EXISTS idx_file_data_file_id ON file_data(file_id);";

    char *err_msg = NULL;
     
    // выполнение невероятных запросов
    rc = sqlite3_exec(db, sql_files, NULL, NULL, &err_msg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Ошибка (sql_files): %s\n", err_msg);
        sqlite3_free(err_msg);
        return -1;
    }

    rc = sqlite3_exec(db, sql_data, NULL, NULL, &err_msg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Ошибка (sql_data): %s\n", err_msg);
        sqlite3_free(err_msg);
        return -1;
    }

    rc = sqlite3_exec(db, sql_indexes, NULL, NULL, &err_msg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Ошибка (sql_indexes): %s\n", err_msg);
        sqlite3_free(err_msg);
        return -1;
    }

    /* СОЗДАНИЕ КОРНЕВОЙ ДИРЕКТОРИИ, ЕСЛИ ЕЕ НЕТ
    S_IFDIR | 0755
    - S_IFDIR = 0040000 - флаг директории
    - 0755 = rwxr-xr-x 
    - 0040755
    */
    const char *check_root = "SELECT id FROM files WHERE path = '/';";
    sqlite3_stmt *stmt;
    rc = sqlite3_prepare_v3(db, check_root, -1, 0, &stmt, NULL);

    if (rc == SQLITE_OK && sqlite3_step(stmt) != SQLITE_ROW) {
        sqlite3_finalize(stmt);

        double now = (double)time(NULL);
        uid_t uid = getuid();
        gid_t gid = getgid();

        const char *insert_root = 
            "INSERT INTO files (path, mode, uid, gid, size, atime, mtime, ctime, nlink)"
            "VALUES ('/', ?, ?, ?, 0, ?, ?, ?, 2);"; // nlink=2 для . и ..
        
        sqlite3_prepare_v3(db, insert_root, -1, 0, &stmt, NULL);
        sqlite3_bind_int(stmt, 1, S_IFDIR | 0755);
        sqlite3_bind_int(stmt, 2, uid);
        sqlite3_bind_int(stmt, 3, gid);
        sqlite3_bind_double(stmt, 4, now);
        sqlite3_bind_double(stmt, 5, now);
        sqlite3_bind_double(stmt, 6, now);
        sqlite3_step(stmt);
    }
    sqlite3_finalize(stmt);

    printf("БД инициализирована: %s\n", DB_PATH);
    return 0;
}

/*  тут id файла по пути

прямой поиск по полному пути
*/

static int get_file_id(const char *path) {
    const char * sql = "SELECT id FROM files WHERE path = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -1;

    sqlite3_bind_text(stmt, 1, path, -1, SQLITE_TRANSIENT);

    int file_id = -1;
    if (sqlite3_step(stmt) == SQLITE_ROW) { // такая запись есть
        file_id = sqlite3_column_int(stmt, 0);
    }
    sqlite3_finalize(stmt);
    return file_id;
}

/*
    получение атрибутов файла
для ls, stat, cat ...

структура stat:
    st_mode: - тип + права 
    st_nlink: - количество ссылок
    st_size: размер в байтах
    st_uid, st_gid: понятно
    st_atime, m, c: времена
*/

static int fs_getattr(const char *path, struct stat *stbuf) {
    memset(stbuf, 0, sizeof(struct stat));

    const char *sql = 
    "SELECT mode, uid, gid, size, atime, mtime, ctime, nlink "
    "FROM files WHERE path = ?;";

    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_text(stmt, 1, path, -1, SQLITE_STATIC);

    if (sqlite3_step(stmt) == SQLITE_ROW) {
        stbuf->st_mode = sqlite3_column_int(stmt,0);
        stbuf->st_uid = sqlite3_column_int(stmt,1);
        stbuf->st_gid = sqlite3_column_int(stmt,2);
        stbuf->st_size = sqlite3_column_int64(stmt,3);
        stbuf->st_atime = (time_t)sqlite3_column_double(stmt,4);
        stbuf->st_mtime = (time_t)sqlite3_column_double(stmt,5);
        stbuf->st_ctime = (time_t)sqlite3_column_double(stmt,6);
        stbuf->st_nlink = sqlite3_column_int(stmt,7);

        sqlite3_finalize(stmt);
        return 0;
    }

    sqlite3_finalize(stmt);
    return -ENOENT;
}

/*
    ЧТЕНИЕ СОДЕРЖИМОГО для ls, find

1 проверка, что это директория
2 . и ..
3 все файлы/директории, чей путь начинается с path/
4 Для каждого filler() - имя в результат
*/

static int fs_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
                      off_t offset, struct fuse_file_info *fi) {
    (void) offset;
    (void) fi;

    // чек что это директория
    const char *check_dir = "SELECT mode FROM files WHERE path = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, check_dir, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_text(stmt, 1, path, -1, SQLITE_STATIC);

    if (sqlite3_step(stmt) == SQLITE_ROW) {
        int mode = sqlite3_column_int(stmt, 0);
        if (!S_ISDIR(mode)) {
            sqlite3_finalize(stmt);
            return -ENOTDIR;
        }
    } else {
        sqlite3_finalize(stmt);
        return -ENOENT;
    }
    sqlite3_finalize(stmt);

    // . и ..
    filler(buf, ".", NULL, 0);
    filler(buf, "..", NULL, 0);

        /* поиск детей директории
        НО НЕ: /dir/subdir/file...

        path LIKE '/dir/%' 
        "*/

    char pattern[1024];
    if (strcmp(path, "/") == 0) {
        // для корня
        strcpy(pattern, "/%");
    } else {
        // /dir:
        snprintf(pattern, sizeof(pattern), "%s/%%", path);
    }

    const char *sql = "SELECT path FROM files WHERE path LIKE ? AND path != ?;";
    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_text(stmt, 1, pattern, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, path, -1, SQLITE_STATIC);

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        const char *child_path = (const char *)sqlite3_column_text(stmt, 0);

        // ТОЛЬКО ИМЯ ФАЙЛА
        const char *name = strrchr(child_path, '/');
        if (name) {
            name ++; // пропуск

            // прямой ребенок?
            const char *prefix = (strcmp(path, "/") == 0) ? "/" : path;
            int prefix_len = strlen(prefix);
            if (strcmp(prefix, "/") == 0) prefix_len = 0;

            const char *remainder = child_path + prefix_len + 1;
            if (strchr(remainder, '/') == NULL) {
                filler(buf, name, NULL, 0);
            }
        }
    }

    sqlite3_finalize(stmt);
    return 0;
}

/*
    Создание директории
*/

static int fs_mkdir(const char *path, mode_t mode) {
    if (get_file_id(path) >= 0) {
        return -EEXIST;
    }

    // проверка родительской
    char parent_path[1024];
    strncpy(parent_path, path, sizeof(parent_path) - 1);
    char *last_slash = strrchr(parent_path, '/');
    if (last_slash) {
        if (last_slash == parent_path) {
            strcpy(parent_path, "/");
        } else {
            *last_slash = '\0';
        }
    }

    if (get_file_id(parent_path) < 0) {
        return -ENOENT;
    }

    double now = (double)time(NULL);
    uid_t uid = getuid();
    gid_t gid = getgid();

    const char *sql = 
        "INSERT INTO files (path, mode, uid, gid, size, atime, mtime, ctime, nlink) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?, 2);"; // nlink=2 для . и ..

    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    
    sqlite3_bind_text(stmt, 1, path, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 2, S_IFDIR | (mode & 0777));
    sqlite3_bind_int(stmt, 3, uid);
    sqlite3_bind_int(stmt, 4, gid);
    sqlite3_bind_double(stmt, 5, now);
    sqlite3_bind_double(stmt, 6, now);
    sqlite3_bind_double(stmt, 7, now);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -EIO;
}

/* 
    удаление директории (rmdir)
*/
static int fs_rmdir(const char *path) {
    int file_id = get_file_id(path);
    if (file_id < 0) return -ENOENT;

    // проверка директория?
    const char *check = "SELECT mode FROM files WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, check, -1 , &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);

    if (sqlite3_step(stmt) == SQLITE_ROW) {
        if (!S_ISDIR(sqlite3_column_int(stmt, 0))) {
            sqlite3_finalize(stmt);
            return -ENOTDIR;
        }
    }
    sqlite3_finalize(stmt);

    // Пустая?
    char pattern[1024];
    snprintf(pattern, sizeof(pattern), "%s/%%", path);

    const char *check_empty = "SELECT COUNT(*) FROM files WHERE path LIKE ?;";
    rc = sqlite3_prepare_v2(db, check_empty, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_text(stmt, 1, pattern, -1, SQLITE_STATIC);
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        if (sqlite3_column_int(stmt, 0) > 0) {
            sqlite3_finalize(stmt);
            return -ENOTEMPTY;
        }
    }
    sqlite3_finalize(stmt);

    // удаление
    const char *sql = "DELETE FROM files WHERE id = ?;";
    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -EIO;
}

/*
    СОЗДАНИЕ ФАЙЛА
*/
static int fs_create(const char *path, mode_t mode, struct fuse_file_info *fi) {
    if (get_file_id(path) >= 0) return -EEXIST;
    char parent_path[1024];
    strncpy(parent_path, path, sizeof(parent_path) - 1);
    char *last_slash = strrchr(parent_path, '/');
    if (last_slash) {
        if (last_slash == parent_path) {
            strcpy(parent_path, "/");
        } else {
            *last_slash = '\0';
        }
    }

    if (get_file_id(parent_path) < 0) return -ENOENT;

    double now = (double)time(NULL);
    uid_t uid = getuid();
    gid_t gid = getgid();   

    const char *sql = 
        "INSERT INTO files (path, mode, uid, gid, size, atime, mtime, ctime, nlink) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?, 1);"; // nlink=1 для файла
    
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_text(stmt,1, path, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 2, S_IFREG | (mode & 0777));
    sqlite3_bind_int(stmt, 3, uid);
    sqlite3_bind_int(stmt, 4, gid);
    sqlite3_bind_double(stmt, 5, now);
    sqlite3_bind_double(stmt, 6, now);
    sqlite3_bind_double(stmt, 7, now);
    
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) return -EIO;

    int file_id = get_file_id(path);
    fi->fh = file_id;

    return 0;
}


static int fs_open(const char *path, struct fuse_file_info *fi) {
    int file_id = get_file_id(path);
    if (file_id < 0) return -ENOENT;

    const char *sql = "SELECT mode FROM files WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        if (S_ISDIR(sqlite3_column_int(stmt, 0))) {
            sqlite3_finalize(stmt);
            return -EISDIR;
        }
    }
    sqlite3_finalize(stmt);

    fi->fh = file_id;
    return 0;
}

/*
    ЧТЕНИЕ ДАННЫХ ИЗ ФАЙЛА
*/
static int fs_read(const char *path, char *buf, size_t size, off_t offset,
                   struct fuse_file_info *fi) {
    (void) path;

    int file_id = fi->fh;

    const char *sql_size = "SELECT size FROM files WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql_size, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);

    size_t file_size = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        file_size = sqlite3_column_int64(stmt, 0);
    } else {
        sqlite3_finalize(stmt);
        return 0;
    }
    sqlite3_finalize(stmt);

    // Если оффсет за пределами файла
    if (offset >= (off_t)file_size) return 0;

    // Корректировка size
    if (offset + size > file_size) {
        size = file_size - offset;
    }

    // Диапазон чанков
    int start_chunk = offset / CHUNK_SIZE;
    int end_chunk = (offset + size - 1) / CHUNK_SIZE;

    size_t bytes_read = 0;

    // чтение нужных
    for (int chunk_idx = start_chunk; chunk_idx <= end_chunk; chunk_idx++) {
        const char *sql = 
            "SELECT data FROM file_data WHERE file_id = ? AND chunk_index = ?;";
        rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
        if (rc != SQLITE_OK) return -EIO;

        sqlite3_bind_int(stmt, 1, file_id);
        sqlite3_bind_int(stmt, 2, chunk_idx);

        if (sqlite3_step(stmt) == SQLITE_ROW) {
            const void *data = sqlite3_column_blob(stmt, 0);
            int data_size = sqlite3_column_bytes(stmt, 0);

            // смещения внутри чанка
            off_t chunk_offset = chunk_idx * CHUNK_SIZE;
            size_t start_offset = (offset > chunk_offset) ? offset - chunk_offset : 0;
            size_t end_offset = ((offset + size) < (chunk_offset + data_size)) ? 
                                (offset + size - chunk_offset) : data_size;

            if (start_offset < end_offset) {
                size_t to_copy = end_offset - start_offset;
                memcpy(buf + bytes_read, (char *)data + start_offset, to_copy);
                bytes_read += to_copy;
            }
        }
        sqlite3_finalize(stmt);
    }
    /*  atime
    */
    double now = (double)time(NULL);
    const char *update_atime = "UPDATE files SET atime = ? WHERE id = ?;";
    sqlite3_prepare_v2(db, update_atime, -1, &stmt, NULL);
    sqlite3_bind_double(stmt, 1, now);
    sqlite3_bind_int(stmt, 2, file_id);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return bytes_read;
}

/*
    ЗАПИСЬ ЧАНКАМИ
*/
static int fs_write(const char *path, const char *buf, size_t size,
                    off_t offset, struct fuse_file_info *fi) {
    (void) path; // предупреждение
    int file_id = fi->fh;

    // текущий размер
    const char *sql_select = "SELECT size FROM files WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql_select, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);

    size_t old_size = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) { 
        old_size = sqlite3_column_int64(stmt, 0);
    }
    sqlite3_finalize(stmt);

    size_t new_size = (offset + size > old_size) ? (offset + size) : old_size;

    // Диапазон чанков
    int start_chunk = offset / CHUNK_SIZE;
    int end_chunk = (offset + size - 1) / CHUNK_SIZE;

    size_t bytes_written = 0;

    for(int chunk_idx = start_chunk; chunk_idx <= end_chunk; chunk_idx++) {
        const char *sql_read = "SELECT data FROM file_data WHERE file_id = ? AND chunk_index = ?;";
        rc = sqlite3_prepare_v2(db, sql_read, -1, &stmt, NULL);
        if (rc != SQLITE_OK) return -EIO;
    
        sqlite3_bind_int(stmt, 1, file_id);
        sqlite3_bind_int(stmt, 2, chunk_idx);
    
        char chunk_data[CHUNK_SIZE];    
        memset(chunk_data, 0, CHUNK_SIZE);
        size_t existing_chunk_size = 0;
    
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            const void *existing_data = sqlite3_column_blob(stmt, 0);
            existing_chunk_size = sqlite3_column_bytes(stmt, 0);
            memcpy(chunk_data, existing_data, existing_chunk_size); 
        }
        sqlite3_finalize(stmt);
    
    // Границы записи в этот чанк
    size_t chunk_offset = (chunk_idx == start_chunk) ? (offset % CHUNK_SIZE) : 0;
    size_t bytes_to_write = CHUNK_SIZE - chunk_offset;

    if (bytes_written + bytes_to_write > size) {
        bytes_to_write = size - bytes_written;
    }

    // новые данные в буфер чанка
    memcpy(chunk_data + chunk_offset, buf + bytes_written, bytes_to_write);

    // размер чанка
    size_t chunk_data_size = chunk_offset + bytes_to_write;
    if (chunk_data_size < existing_chunk_size) {
        chunk_data_size = existing_chunk_size;  
    }
    // сейв чанка
    const char *sql_upsert = 
        "INSERT OR REPLACE INTO file_data (file_id, chunk_index, data) values (?, ?, ?);";
    rc = sqlite3_prepare_v2(db, sql_upsert, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;   

    sqlite3_bind_int(stmt, 1, file_id);
    sqlite3_bind_int(stmt, 2, chunk_idx);
    sqlite3_bind_blob(stmt, 3, chunk_data, chunk_data_size, SQLITE_TRANSIENT);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if(rc != SQLITE_DONE) {
        return -EIO;
    }

    bytes_written += bytes_to_write;
    }
    
    double now = (double)time(NULL);
    const char *sql_meta = 
        "UPDATE files SET size = ?, mtime = ?, ctime = ? WHERE id = ?;";
    sqlite3_prepare_v2(db, sql_meta, -1, &stmt, NULL);
    sqlite3_bind_int64(stmt, 1, new_size);
    sqlite3_bind_double(stmt, 2, now);  
    sqlite3_bind_double(stmt, 3, now);
    sqlite3_bind_int(stmt, 4, file_id);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return size;
}
/*
    УДАЛЕНИЕ ФАЙЛА(unlink)
*/
static int fs_unlink(const char *path) {
    int file_id = get_file_id(path);
    if (file_id < 0) return -ENOENT;
    
    const char *check = "SELECT mode FROM files WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, check, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        if (S_ISDIR(sqlite3_column_int(stmt, 0))) {
            sqlite3_finalize(stmt);
            return -EISDIR;
        }
    }
    sqlite3_finalize(stmt);

    // данные удалятся каскадом
    const char *sql = "DELETE FROM files WHERE id = ?;";
    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -EIO;
}

// РАЗМЕР ФАЙЛА (truncate)

static int fs_truncate(const char *path, off_t size) {
    int file_id = get_file_id(path);
    if (file_id < 0) {
        return -ENOENT;
    }

    // текущий размер
    const char *sql_size = "SELECT size FROM files WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql_size, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);

    size_t old_size = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) { 
        old_size = sqlite3_column_int64(stmt, 0);
    }
    sqlite3_finalize(stmt);

    int new_last_chunk = (size > 0) ? ((size - 1) / CHUNK_SIZE) : -1;
    int old_last_chunk = (old_size > 0) ? ((old_size - 1) / CHUNK_SIZE) : -1;

    if (size < old_size) {
        // уменьшение
        const char *sql_del = "DELETE FROM file_data WHERE file_id = ? and chunk_index > ?;";
        sqlite3_prepare_v2(db, sql_del, -1, &stmt, NULL);
        sqlite3_bind_int(stmt, 1, file_id);
        sqlite3_bind_int(stmt, 2, new_last_chunk);
        sqlite3_step(stmt);
        sqlite3_finalize(stmt);

        // последний чанк 
        if (new_last_chunk >= 0) {
            size_t chunk_size = size % CHUNK_SIZE;
            if (chunk_size == 0) chunk_size = CHUNK_SIZE;

            const char *sql_read = "SELECT data FROM file_data WHERE file_id = ? AND chunk_index = ?;";
            sqlite3_prepare_v2(db, sql_read, -1, &stmt, NULL);
            sqlite3_bind_int(stmt, 1, file_id);
            sqlite3_bind_int(stmt, 2, new_last_chunk); 

            if (sqlite3_step(stmt) == SQLITE_ROW) {
                const void *data = sqlite3_column_blob(stmt, 0);
                size_t current_size = sqlite3_column_bytes(stmt, 0);

                if (current_size > chunk_size) {
                    char *truncated = malloc(chunk_size);
                    memcpy(truncated, data, chunk_size);

                    sqlite3_finalize(stmt);

                    const char *sql_update = "UPDATE file_data SET data = ? WHERE file_id = ? AND chunk_index = ?;";
                    sqlite3_prepare_v2(db, sql_update, -1, &stmt, NULL);
                    sqlite3_bind_blob(stmt, 1, truncated, chunk_size, SQLITE_TRANSIENT);
                    sqlite3_bind_int(stmt, 2, file_id);
                    sqlite3_bind_int(stmt, 3, new_last_chunk);
                    sqlite3_step(stmt);
                    sqlite3_finalize(stmt);

                    free(truncated);
                } else {
                    sqlite3_finalize(stmt);
                } 
            } else {
                sqlite3_finalize(stmt);
            }
        }
    } else if (size > old_size) {
        // увеличение - ничего не делаем, данные будут записаны позже
    }

    // новый размер
    double now = (double)time(NULL);
    const char *sql_meta = "UPDATE files SET size = ?, mtime = ? WHERE id = ?;";
    sqlite3_prepare_v2(db, sql_meta, -1, &stmt, NULL);
    sqlite3_bind_int64(stmt, 1, size);
    sqlite3_bind_double(stmt, 2, now);  
    sqlite3_bind_int(stmt, 3, file_id);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return 0;
}

/*
Дополнительные требования (для отличной оценки)
    • Изменение прав доступа (chmod)
    • Изменение владельца (chown)
    • Переименование файлов (rename)
    • Изменение размера файла (truncate)
    • Обновление времени доступа (utimens)
    • Чанковое хранение для больших файлов
    • Unit-тесты с покрытием > 80%
*/
// CHMOD
static int fs_chmod(const char *path, mode_t mode) {
    int file_id = get_file_id(path);
    if (file_id < 0) {
        return -ENOENT;
    }

    const char *sql_get = "SELECT mode FROM files WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql_get, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_int(stmt, 1, file_id);

    mode_t old_mode = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        old_mode = sqlite3_column_int(stmt, 0);
    }
    sqlite3_finalize(stmt);

    // сейв типа файла + новые права
    mode_t new_mode = (old_mode & S_IFMT) | (mode & 0777);
    
    const char* sql = "UPDATE files SET mode = ?, ctime = ? WHERE id = ?;";
    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    double now = (double)time(NULL);
    sqlite3_bind_int(stmt, 1, new_mode);
    sqlite3_bind_double(stmt, 2, now);
    sqlite3_bind_int(stmt, 3, file_id);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);
    
    return (rc == SQLITE_DONE) ? 0 : -EIO;
}

// CHOWN
static int fs_chown(const char *path, uid_t uid, gid_t gid) {
    int file_id = get_file_id(path);
    if (file_id < 0) return -ENOENT;

    const char *sql = "UPDATE files SET uid = ?, gid = ?, ctime = ? WHERE id = ?;";
    sqlite3_stmt *stmt; 
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    double now = (double)time(NULL);
    sqlite3_bind_int(stmt, 1, uid);
    sqlite3_bind_int(stmt, 2, gid);
    sqlite3_bind_double(stmt, 3, now);
    sqlite3_bind_int(stmt, 4, file_id);
    
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -EIO;
}

// RENAME
static int fs_rename(const char *oldpath, const char *newpath) {
    int file_id = get_file_id(oldpath);
    if (file_id < 0) return -ENOENT;

    if (get_file_id(newpath) >= 0) return -EEXIST;

    // Проверяем, что родительская директория newpath существует
    char parent_path[1024];
    strncpy(parent_path, newpath, sizeof(parent_path) - 1);
    char *last_slash = strrchr(parent_path, '/');
    if (last_slash) {
        if (last_slash == parent_path) {
            strcpy(parent_path, "/");
        } else {
            *last_slash = '\0';
        }
    }

    if (get_file_id(parent_path) < 0) return -ENOENT;

    const char *sql = "UPDATE files SET path = ?, ctime = ? WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;   

    double now = (double)time(NULL);
    sqlite3_bind_text(stmt, 1, newpath, -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(stmt, 2, now);
    sqlite3_bind_int(stmt, 3, file_id);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    // обновляем пути всех дочерних файлов/директорий
    char old_prefix[1024], new_prefix[1024];
    snprintf(old_prefix, sizeof(old_prefix), "%s/%%", oldpath);

    const char *sql_chldren = "SELECT id, path FROM files WHERE path LIKE ?;";
    rc = sqlite3_prepare_v2(db, sql_chldren, -1, &stmt, NULL);
    if (rc == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, old_prefix, -1, SQLITE_STATIC);
    
        while(sqlite3_step(stmt) == SQLITE_ROW) {
            int child_id = sqlite3_column_int(stmt, 0);
            const char *child_path = (const char *)sqlite3_column_text(stmt, 1);

            // новый путь
            char new_child_path[1024];
            snprintf(new_child_path, sizeof(new_child_path), "%s%s", 
                     newpath, child_path + strlen(oldpath));

            const char *sql_update = "UPDATE files SET path = ?, ctime = ? WHERE id = ?;";
            sqlite3_stmt *stmt_update;
            sqlite3_prepare_v2(db, sql_update, -1, &stmt_update, NULL);
            sqlite3_bind_text(stmt_update, 1, new_child_path, -1, SQLITE_TRANSIENT);
            sqlite3_bind_double(stmt_update, 2, now);
            sqlite3_bind_int(stmt_update, 3, child_id);
            sqlite3_step(stmt_update);
            sqlite3_finalize(stmt_update);
        }
        sqlite3_finalize(stmt);
    }
    return (rc == SQLITE_DONE || rc == SQLITE_ROW) ? 0 : -EIO;
}

// UTIMENS
static int fs_utimens(const char *path, const struct timespec tv[2]) {
    int file_id = get_file_id(path);
    if (file_id < 0) return -ENOENT;
    
    double atime = (double)tv[0].tv_sec + (double)tv[0].tv_nsec / 1e9;
    double mtime = (double)tv[1].tv_sec + (double)tv[1].tv_nsec / 1e9;

    const char *sql = "UPDATE files SET atime = ?, mtime = ? WHERE id = ?;";
    sqlite3_stmt *stmt;
    int rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -EIO;

    sqlite3_bind_double(stmt, 1, atime);
    sqlite3_bind_double(stmt, 2, mtime);    
    sqlite3_bind_int(stmt, 3, file_id);

    rc = sqlite3_step(stmt);    
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -EIO;
}

/*
    ИНИЦИАЛИЗАЦИЯ
*/
static void *fs_init(struct fuse_conn_info *conn) {
    (void) conn;
    if (init_database() < 0) {
        fprintf(stderr, "Ошибка в инициализации БД\n");
        exit(1);
    }
    printf("FUSE SQLite ФС инициализирована\n");
    printf("БД: %s\n", DB_PATH);
    printf("Размер чанка: %d байт(%.1f МБ)\n", CHUNK_SIZE, CHUNK_SIZE / (1024.0 * 1024.0));
    return NULL;
}

static void fs_destroy(void *private_data) {
    (void) private_data;
    if (db != NULL) {
        sqlite3_close(db);
        printf("БД закрыта\n");
    }
}
/*
регистрация операций FUSE
*/

static struct fuse_operations fs_operations = {
    .init       = fs_init,
    .destroy    = fs_destroy,
    .getattr    = fs_getattr,
    .readdir    = fs_readdir,
    .mkdir      = fs_mkdir,
    .rmdir      = fs_rmdir,
    .create     = fs_create,
    .open       = fs_open,
    .read       = fs_read,
    .write      = fs_write,
    .unlink     = fs_unlink,
    // дополнительные
    .truncate   = fs_truncate,
    .chmod      = fs_chmod,
    .chown      = fs_chown,
    .rename     = fs_rename,
    .utimens    = fs_utimens,
};

// main
int main(int argc, char *argv[]) {
    // 
    printf("════════════════════════════════════════════════════════════\n");
    printf("  FUSE SQLite Файловая Система\n");
    printf("════════════════════════════════════════════════════════════\n\n");

    return fuse_main(argc, argv, &fs_operations, NULL);
}
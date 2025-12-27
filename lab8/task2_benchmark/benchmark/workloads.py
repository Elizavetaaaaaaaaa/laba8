"""Определения типов нагрузок (workloads)"""


class WorkloadConfig:
    """Конфигурация нагрузки"""
    
    # Sequential Write/Read
    SEQUENTIAL_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
    SEQUENTIAL_FILES = 100
    
    # Random I/O
    RANDOM_BLOCK_SIZE = 4 * 1024  # 4 KB
    RANDOM_OPERATIONS = 1000
    
    # Small Files
    SMALL_FILE_SIZE = 4 * 1024  # 4 KB
    SMALL_FILES_COUNT = 1000
    
    # Metadata Operations
    METADATA_OPERATIONS = 5000


class WorkloadType:
    """Типы нагрузок"""
    SEQUENTIAL_WRITE = "sequential_write"
    SEQUENTIAL_READ = "sequential_read"
    RANDOM_IO = "random_io"
    SMALL_FILES = "small_files"
    METADATA_OPS = "metadata_ops"

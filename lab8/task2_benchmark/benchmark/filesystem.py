"""Бенчмарки для смонтированных файловых систем (s3fs, goofys)"""

import os
import random
from pathlib import Path
from .base import BenchmarkBase
from .workloads import WorkloadConfig


class FilesystemBenchmark(BenchmarkBase):
    """Бенчмарк для смонтированной ФС"""
    
    def __init__(self, storage_type: str, mount_point: str, workload_type: str):
        super().__init__(workload_type, storage_type)
        self.mount_point = Path(mount_point)
        self.workload_type = workload_type
        self.test_dir = self.mount_point / f"benchmark_{workload_type}"
        self.test_data = None
        self.test_files = []

    def setup(self):
        """Создание тестовой директории"""
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Подготовка данных для sequential/small files
        if self.workload_type in ["sequential_write", "sequential_read"]:
            self.test_data = os.urandom(WorkloadConfig.SEQUENTIAL_FILE_SIZE)
        elif self.workload_type == "small_files":
            self.test_data = os.urandom(WorkloadConfig.SMALL_FILE_SIZE)
        elif self.workload_type == "random_io":
            # Создаем большой файл для random I/O
            big_file = self.test_dir / "random_io_file.dat"
            with open(big_file, 'wb') as f:
                f.write(os.urandom(10 * 1024 * 1024))  # 10 MB файл
            self.test_files = [big_file]

    def run_iteration(self) -> float:
        """Выполнение одной итерации в зависимости от типа нагрузки"""
        
        if self.workload_type == "sequential_write":
            return self._sequential_write()
        elif self.workload_type == "sequential_read":
            return self._sequential_read()
        elif self.workload_type == "random_io":
            return self._random_io()
        elif self.workload_type == "small_files":
            return self._small_file_create()
        elif self.workload_type == "metadata_ops":
            return self._metadata_operation()
        
        return 0.0

    def _sequential_write(self) -> float:
        """Последовательная запись"""
        file_path = self.test_dir / f"seq_{len(self.test_files)}.dat"
        with open(file_path, 'wb') as f:
            f.write(self.test_data)
        self.test_files.append(file_path)
        return len(self.test_data)

    def _sequential_read(self) -> float:
        """Последовательное чтение"""
        # Сначала создаем файлы если их нет
        if not self.test_files:
            for i in range(WorkloadConfig.SEQUENTIAL_FILES):
                file_path = self.test_dir / f"seq_{i}.dat"
                with open(file_path, 'wb') as f:
                    f.write(self.test_data)
                self.test_files.append(file_path)
        
        # Читаем случайный файл
        file_path = random.choice(self.test_files)
        with open(file_path, 'rb') as f:
            data = f.read()
        return len(data)

    def _random_io(self) -> float:
        """Случайное чтение блоков"""
        file_path = self.test_files[0]
        file_size = file_path.stat().st_size
        
        # Случайная позиция
        offset = random.randint(0, max(0, file_size - WorkloadConfig.RANDOM_BLOCK_SIZE))
        
        with open(file_path, 'rb') as f:
            f.seek(offset)
            data = f.read(WorkloadConfig.RANDOM_BLOCK_SIZE)
        
        return len(data)

    def _small_file_create(self) -> float:
        """Создание маленького файла"""
        file_path = self.test_dir / f"small_{len(self.test_files)}.dat"
        with open(file_path, 'wb') as f:
            f.write(self.test_data)
        self.test_files.append(file_path)
        return len(self.test_data)

    def _metadata_operation(self) -> float:
        """Операции с метаданными (stat, create, delete)"""
        test_file = self.test_dir / f"meta_{len(self.test_files)}.dat"
        
        # Create
        test_file.write_bytes(b"test")
        
        # Stat
        test_file.stat()
        
        # Delete
        test_file.unlink()
        
        return 4  # байты записаны

    def cleanup(self):
        """Очистка тестовых файлов"""
        try:
            for f in self.test_files:
                if f.exists():
                    f.unlink()
            
            if self.test_dir.exists():
                # Удаляем оставшиеся файлы
                for f in self.test_dir.iterdir():
                    if f.is_file():
                        f.unlink()
                self.test_dir.rmdir()
        except Exception as e:
            print(f"  Cleanup warning: {e}")

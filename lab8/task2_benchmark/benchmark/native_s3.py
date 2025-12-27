"""Бенчмарки для Native S3 API (boto3)"""

import os
import io
import random
import boto3
from .base import BenchmarkBase
from .workloads import WorkloadConfig


class NativeS3Benchmark(BenchmarkBase):
    """Бенчмарк для нативного S3 API через boto3"""
    
    def __init__(self, bucket_name: str, workload_type: str, 
                 endpoint_url: str = None, access_key: str = None, 
                 secret_key: str = None):
        super().__init__(workload_type, "native_s3")
        self.bucket_name = bucket_name
        self.workload_type = workload_type
        self.test_data = None
        self.test_keys = []
        
        # Инициализация S3 клиента
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key or os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
            aws_secret_access_key=secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin123')
        )

    def setup(self):
        """Подготовка данных и bucket"""
        # Создаем bucket если не существует
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except:
            self.s3_client.create_bucket(Bucket=self.bucket_name)
        
        # Подготовка данных
        if self.workload_type in ["sequential_write", "sequential_read"]:
            self.test_data = os.urandom(WorkloadConfig.SEQUENTIAL_FILE_SIZE)
        elif self.workload_type == "small_files":
            self.test_data = os.urandom(WorkloadConfig.SMALL_FILE_SIZE)
        elif self.workload_type == "random_io":
            # Создаем большой объект для random read
            big_data = os.urandom(10 * 1024 * 1024)  # 10 MB
            key = f"benchmark/random_io_file.dat"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=big_data
            )
            self.test_keys = [key]

    def run_iteration(self) -> float:
        """Выполнение итерации"""
        
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
        """Последовательная запись объекта"""
        key = f"benchmark/seq_{len(self.test_keys)}.dat"
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=self.test_data
        )
        self.test_keys.append(key)
        return len(self.test_data)

    def _sequential_read(self) -> float:
        """Последовательное чтение объекта"""
        # Создаем объекты если их нет
        if not self.test_keys:
            for i in range(min(100, WorkloadConfig.SEQUENTIAL_FILES)):
                key = f"benchmark/seq_{i}.dat"
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=self.test_data
                )
                self.test_keys.append(key)
        
        # Читаем случайный объект
        key = random.choice(self.test_keys)
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        data = response['Body'].read()
        return len(data)

    def _random_io(self) -> float:
        """Случайное чтение с использованием Range requests"""
        key = self.test_keys[0]
        
        # Получаем размер объекта
        head = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
        file_size = head['ContentLength']
        
        # Случайная позиция
        offset = random.randint(0, max(0, file_size - WorkloadConfig.RANDOM_BLOCK_SIZE))
        end = offset + WorkloadConfig.RANDOM_BLOCK_SIZE - 1
        
        # Range read
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=key,
            Range=f'bytes={offset}-{end}'
        )
        data = response['Body'].read()
        return len(data)

    def _small_file_create(self) -> float:
        """Создание маленького объекта"""
        key = f"benchmark/small_{len(self.test_keys)}.dat"
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=self.test_data
        )
        self.test_keys.append(key)
        return len(self.test_data)

    def _metadata_operation(self) -> float:
        """Операции с метаданными"""
        key = f"benchmark/meta_{len(self.test_keys)}.dat"
        
        # Create (PUT)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=b"test"
        )
        
        # Head (metadata only)
        self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
        
        # Delete
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        
        return 4

    def cleanup(self):
        """Очистка созданных объектов"""
        try:
            # Удаляем все тестовые объекты
            for key in self.test_keys:
                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                except:
                    pass
            
            # Очищаем префикс benchmark/
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix='benchmark/'
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        self.s3_client.delete_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )
            except Exception as e:
                print(f"  Cleanup warning: {e}")
        except Exception as e:
            print(f"  Cleanup error: {e}")

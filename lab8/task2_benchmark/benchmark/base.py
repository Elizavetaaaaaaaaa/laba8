"""Базовые классы для бенчмарков"""

import time
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class BenchmarkResult:
    """Результаты выполнения бенчмарка"""
    name: str
    storage_type: str
    throughput_mbps: float
    iops: float
    latency_avg_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    errors: int
    total_time_sec: float
    iterations: int

    def to_dict(self):
        return asdict(self)


class BenchmarkBase(ABC):
    """Базовый класс для всех бенчмарков"""
    
    def __init__(self, name: str, storage_type: str):
        self.name = name
        self.storage_type = storage_type
        self.latencies: List[float] = []
        self.errors = 0

    @abstractmethod
    def setup(self):
        """Подготовка перед тестом"""
        pass

    @abstractmethod
    def run_iteration(self) -> float:
        """
        Выполнение одной итерации.
        Возвращает количество обработанных байт.
        """
        pass

    @abstractmethod
    def cleanup(self):
        """Очистка после теста"""
        pass

    def run(self, iterations: int = 100) -> BenchmarkResult:
        """Запуск бенчмарка с указанным количеством итераций"""
        print(f"[{self.storage_type}] Запуск {self.name}...")
        
        self.setup()
        total_bytes = 0
        self.latencies = []
        self.errors = 0
        
        start_time = time.perf_counter()
        
        for i in range(iterations):
            try:
                iter_start = time.perf_counter()
                bytes_processed = self.run_iteration()
                iter_elapsed = time.perf_counter() - iter_start
                
                self.latencies.append(iter_elapsed * 1000)  # в миллисекунды
                total_bytes += bytes_processed
                
                if (i + 1) % max(1, iterations // 10) == 0:
                    print(f"  Progress: {i + 1}/{iterations}")
                    
            except Exception as e:
                print(f"  Error in iteration {i}: {e}")
                self.errors += 1
        
        total_time = time.perf_counter() - start_time
        
        self.cleanup()
        
        return self._calculate_results(total_bytes, total_time, iterations)

    def _calculate_results(self, total_bytes: float, total_time: float, 
                          iterations: int) -> BenchmarkResult:
        """Вычисление метрик из собранных данных"""
        
        if not self.latencies:
            return BenchmarkResult(
                name=self.name,
                storage_type=self.storage_type,
                throughput_mbps=0.0,
                iops=0.0,
                latency_avg_ms=0.0,
                latency_p95_ms=0.0,
                latency_p99_ms=0.0,
                errors=self.errors,
                total_time_sec=total_time,
                iterations=iterations
            )
        
        # Throughput в MB/s
        throughput_mbps = (total_bytes / (1024 * 1024)) / total_time if total_time > 0 else 0
        
        # IOPS (операций в секунду)
        iops = iterations / total_time if total_time > 0 else 0
        
        # Latency статистика
        latencies_arr = np.array(self.latencies)
        latency_avg = np.mean(latencies_arr)
        latency_p95 = np.percentile(latencies_arr, 95)
        latency_p99 = np.percentile(latencies_arr, 99)
        
        return BenchmarkResult(
            name=self.name,
            storage_type=self.storage_type,
            throughput_mbps=throughput_mbps,
            iops=iops,
            latency_avg_ms=latency_avg,
            latency_p95_ms=latency_p95,
            latency_p99_ms=latency_p99,
            errors=self.errors,
            total_time_sec=total_time,
            iterations=iterations
        )

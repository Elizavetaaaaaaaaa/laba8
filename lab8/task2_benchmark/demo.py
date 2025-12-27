#!/usr/bin/env python3
"""
Демонстрация работы benchmark framework с мок-данными
Запускается без настоящего S3 для проверки функционала
"""

import sys
from pathlib import Path

# Добавляем путь к benchmark модулю
sys.path.insert(0, str(Path(__file__).parent))

from benchmark import MetricsCollector, generate_all_plots
from benchmark.base import BenchmarkResult
from benchmark.workloads import WorkloadType
import random


def generate_mock_results():
    """Генерация мок-данных для демонстрации"""
    
    storage_types = ['s3fs', 'goofys', 'native_s3']
    workloads = [
        WorkloadType.SEQUENTIAL_WRITE,
        WorkloadType.SEQUENTIAL_READ,
        WorkloadType.RANDOM_IO,
        WorkloadType.SMALL_FILES,
        WorkloadType.METADATA_OPS
    ]
    
    results = []
    
    # Типичные характеристики для разных storage types
    perf_profiles = {
        's3fs': {
            'throughput_mult': 0.6,  # Медленнее
            'iops_mult': 0.5,
            'latency_mult': 1.8       # Больше задержка
        },
        'goofys': {
            'throughput_mult': 0.85,  # Быстрее s3fs
            'iops_mult': 0.8,
            'latency_mult': 1.3
        },
        'native_s3': {
            'throughput_mult': 1.0,   # Эталон
            'iops_mult': 1.0,
            'latency_mult': 1.0
        }
    }
    
    # Базовые значения для разных workloads
    workload_baseline = {
        WorkloadType.SEQUENTIAL_WRITE: {
            'throughput': 45.0,
            'iops': 45.0,
            'latency': 22.0
        },
        WorkloadType.SEQUENTIAL_READ: {
            'throughput': 52.0,
            'iops': 52.0,
            'latency': 19.0
        },
        WorkloadType.RANDOM_IO: {
            'throughput': 8.5,
            'iops': 2100.0,
            'latency': 0.48
        },
        WorkloadType.SMALL_FILES: {
            'throughput': 3.2,
            'iops': 800.0,
            'latency': 1.25
        },
        WorkloadType.METADATA_OPS: {
            'throughput': 0.5,
            'iops': 125.0,
            'latency': 8.0
        }
    }
    
    for storage in storage_types:
        for workload in workloads:
            profile = perf_profiles[storage]
            baseline = workload_baseline[workload]
            
            # Добавляем небольшой случайный разброс
            noise = 1.0 + (random.random() - 0.5) * 0.1
            
            throughput = baseline['throughput'] * profile['throughput_mult'] * noise
            iops = baseline['iops'] * profile['iops_mult'] * noise
            latency_avg = baseline['latency'] * profile['latency_mult'] * noise
            latency_p95 = latency_avg * 1.6
            latency_p99 = latency_avg * 2.2
            
            result = BenchmarkResult(
                name=workload,
                storage_type=storage,
                throughput_mbps=throughput,
                iops=iops,
                latency_avg_ms=latency_avg,
                latency_p95_ms=latency_p95,
                latency_p99_ms=latency_p99,
                errors=0,
                total_time_sec=100.0 / iops if iops > 0 else 10.0,
                iterations=100
            )
            
            results.append(result)
    
    return results


def main():
    print("=" * 80)
    print("S3 STORAGE BENCHMARK - DEMO MODE")
    print("=" * 80)
    print("Generating mock results to demonstrate framework functionality...")
    print("(Run with real S3 endpoint for actual benchmarks)")
    print("=" * 80)
    print()
    
    # Генерация мок-данных
    results = generate_mock_results()
    
    # Инициализация сборщика метрик
    collector = MetricsCollector()
    
    for result in results:
        collector.add_result(result)
        print(f"✓ {result.storage_type:12} / {result.name:20} → "
              f"{result.throughput_mbps:6.2f} MB/s, "
              f"{result.iops:7.1f} IOPS, "
              f"{result.latency_avg_ms:6.2f}ms")
    
    # Сохранение результатов
    output_dir = Path('benchmark_results_demo')
    
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    
    # Raw data
    collector.save_raw_data(output_dir)
    
    # Report
    collector.generate_report(output_dir)
    
    # Plots
    generate_all_plots(results, output_dir)
    
    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETED")
    print("=" * 80)
    print(f"\nResults saved to: {output_dir.absolute()}")
    print("\nFiles generated:")
    print(f"  • benchmark_raw_*.json")
    print(f"  • benchmark_report_*.txt")
    print(f"  • 01_throughput_comparison.png")
    print(f"  • 02_iops_comparison.png")
    print(f"  • 03_latency_percentiles.png")
    print(f"  • 04_performance_radar.png")
    print()


if __name__ == '__main__':
    main()

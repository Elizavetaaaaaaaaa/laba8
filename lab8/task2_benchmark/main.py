#!/usr/bin/env python3
"""
S3 Storage Benchmark Tool
Сравнение производительности s3fs, goofys и native S3 API
"""
import os
import sys
import argparse
from pathlib import Path

from benchmark import (
    FilesystemBenchmark,
    NativeS3Benchmark,
    MetricsCollector,
    generate_all_plots
)
from benchmark.workloads import WorkloadType, WorkloadConfig


def check_mount_points(s3fs_mount: str = None, goofys_mount: str = None):
    """Проверка доступности точек монтирования"""
    issues = []
    
    if s3fs_mount:
        s3fs_path = Path(s3fs_mount)
        if not s3fs_path.exists():
            issues.append(f"s3fs mount point does not exist: {s3fs_mount}")
        elif not s3fs_path.is_dir():
            issues.append(f"s3fs mount point is not a directory: {s3fs_mount}")
    
    if goofys_mount:
        goofys_path = Path(goofys_mount)
        if not goofys_path.exists():
            issues.append(f"goofys mount point does not exist: {goofys_mount}")
        elif not goofys_path.is_dir():
            issues.append(f"goofys mount point is not a directory: {goofys_mount}")
    
    return issues


def run_workload(storage_type: str, workload_type: str, 
                mount_point: str = None, bucket_name: str = None,
                endpoint_url: str = None, iterations: int = 100,
                access_key: str = None, secret_key: str = None,
    ):
    """Запуск одной нагрузки для одного типа хранилища"""
    
    if storage_type in ['s3fs', 'goofys']:
        if not mount_point:
            print(f"⚠️  Skipping {storage_type}/{workload_type}: mount point not provided")
            return None
        
        benchmark = FilesystemBenchmark(
            storage_type=storage_type,
            mount_point=mount_point,
            workload_type=workload_type
        )
    elif storage_type == 'native_s3':
        if not bucket_name:
            print(f"⚠️  Skipping {storage_type}/{workload_type}: bucket name not provided")
            return None
        
        benchmark = NativeS3Benchmark(
            bucket_name=bucket_name,
            workload_type=workload_type,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key
        )
    else:
        print(f"❌ Unknown storage type: {storage_type}")
        return None
    
    # Определяем количество итераций в зависимости от workload
    if workload_type == WorkloadType.SEQUENTIAL_WRITE:
        iters = min(iterations, WorkloadConfig.SEQUENTIAL_FILES)
    elif workload_type == WorkloadType.SEQUENTIAL_READ:
        iters = min(iterations, WorkloadConfig.SEQUENTIAL_FILES)
    elif workload_type == WorkloadType.RANDOM_IO:
        iters = min(iterations, WorkloadConfig.RANDOM_OPERATIONS)
    elif workload_type == WorkloadType.SMALL_FILES:
        iters = min(iterations, WorkloadConfig.SMALL_FILES_COUNT)
    elif workload_type == WorkloadType.METADATA_OPS:
        iters = min(iterations, WorkloadConfig.METADATA_OPERATIONS)
    else:
        iters = iterations
    
    try:
        result = benchmark.run(iterations=iters)
        return result
    except Exception as e:
        print(f"❌ Error running {storage_type}/{workload_type}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
    SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    parser = argparse.ArgumentParser(
        description='S3 Storage Benchmark Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark all storage types with all workloads
  python3 main.py --bucket benchmark --endpoint http://localhost:9000 \\
      --s3fs-mount /mnt/s3fs --goofys-mount /mnt/goofys

  # Only native S3 API
  python3 main.py --bucket benchmark --endpoint http://localhost:9000 \\
      --storage native_s3

  # Specific workloads
  python3 main.py --bucket benchmark --endpoint http://localhost:9000 \\
      --storage native_s3 --workloads sequential_write sequential_read
        """
    )
    
    parser.add_argument('--bucket', required=True,
                       help='S3 bucket name')
    parser.add_argument('--endpoint', default=None,
                       help='S3 endpoint URL (e.g., http://localhost:9000)')
    parser.add_argument('--s3fs-mount', default=None,
                       help='s3fs mount point (e.g., /mnt/s3fs)')
    parser.add_argument('--goofys-mount', default=None,
                       help='goofys mount point (e.g., /mnt/goofys)')
    parser.add_argument('--storage', nargs='+', 
                       choices=['s3fs', 'goofys', 'native_s3'],
                       default=['native_s3'],
                       help='Storage types to benchmark')
    parser.add_argument('--workloads', nargs='+',
                       choices=[
                           WorkloadType.SEQUENTIAL_WRITE,
                           WorkloadType.SEQUENTIAL_READ,
                           WorkloadType.RANDOM_IO,
                           WorkloadType.SMALL_FILES,
                           WorkloadType.METADATA_OPS
                       ],
                       default=[
                           WorkloadType.SEQUENTIAL_WRITE,
                           WorkloadType.SEQUENTIAL_READ,
                           WorkloadType.RANDOM_IO,
                           WorkloadType.SMALL_FILES,
                           WorkloadType.METADATA_OPS
                       ],
                       help='Workload types to run')
    parser.add_argument('--iterations', type=int, default=100,
                       help='Number of iterations per workload')
    parser.add_argument('--output-dir', default='benchmark_results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Проверяем mount points для FUSE решений
    if 's3fs' in args.storage or 'goofys' in args.storage:
        issues = check_mount_points(args.s3fs_mount, args.goofys_mount)
        if issues:
            print("⚠️  Mount point issues detected:")
            for issue in issues:
                print(f"   - {issue}")
            print("\nℹ️  You can skip FUSE benchmarks by using: --storage native_s3")
            sys.exit(1)
    
    print("=" * 80)
    print("S3 STORAGE BENCHMARK")
    print("=" * 80)
    print(f"Bucket:       {args.bucket}")
    print(f"Endpoint:     {args.endpoint or 'default'}")
    print(f"Storage:      {', '.join(args.storage)}")
    print(f"Workloads:    {', '.join(args.workloads)}")
    print(f"Iterations:   {args.iterations}")
    print(f"Output:       {args.output_dir}")
    print("=" * 80)
    print()
    
    # Инициализация сборщика метрик
    collector = MetricsCollector()
    
    # Запуск всех комбинаций storage × workload
    total = len(args.storage) * len(args.workloads)
    current = 0
    
    for storage_type in args.storage:
        for workload_type in args.workloads:
            current += 1
            print(f"\n[{current}/{total}] Running {storage_type} / {workload_type}...")
            print("-" * 80)
            
            # Определяем параметры в зависимости от типа хранилища
            if storage_type == 's3fs':
                mount_point = args.s3fs_mount
            elif storage_type == 'goofys':
                mount_point = args.goofys_mount
            else:
                mount_point = None
            
            result = run_workload(
                storage_type=storage_type,
                workload_type=workload_type,
                mount_point=mount_point,
                bucket_name=args.bucket,
                endpoint_url=args.endpoint,
                access_key=ACCESS_KEY,
                iterations=args.iterations,
                secret_key=SECRET_KEY
            )
            
            if result:
                collector.add_result(result)
                print(f"✅ Completed: {result.throughput_mbps:.2f} MB/s, "
                     f"{result.iops:.2f} IOPS, "
                     f"{result.latency_avg_ms:.2f}ms avg latency")
    
    # Сохранение результатов
    output_dir = Path(args.output_dir)
    
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    
    # Raw data
    collector.save_raw_data(output_dir)
    
    # Report
    collector.generate_report(output_dir)
    
    # Plots
    if collector.results:
        generate_all_plots(collector.results, output_dir)
    
    print("\n" + "=" * 80)
    print("✅ BENCHMARK COMPLETED")
    print("=" * 80)
    print(f"\nResults saved to: {output_dir.absolute()}")
    print("\nFiles generated:")
    print(f"  • benchmark_raw_*.json       - Raw data for reproducibility")
    print(f"  • benchmark_report_*.txt     - Detailed text report")
    print(f"  • 01_throughput_comparison.png")
    print(f"  • 02_iops_comparison.png")
    print(f"  • 03_latency_percentiles.png")
    print(f"  • 04_performance_radar.png")
    print()


if __name__ == '__main__':
    main()

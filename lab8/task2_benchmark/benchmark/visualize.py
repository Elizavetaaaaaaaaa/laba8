"""Визуализация результатов бенчмарков"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List
from .base import BenchmarkResult


def generate_all_plots(results: List[BenchmarkResult], output_dir: Path):
    """Генерация всех графиков"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n📊 Generating plots...")
    
    # 1. Throughput comparison
    plot_throughput_comparison(results, output_dir / "01_throughput_comparison.png")
    
    # 2. IOPS comparison
    plot_iops_comparison(results, output_dir / "02_iops_comparison.png")
    
    # 3. Latency percentiles
    plot_latency_percentiles(results, output_dir / "03_latency_percentiles.png")
    
    # 4. Overall performance radar
    plot_performance_radar(results, output_dir / "04_performance_radar.png")
    
    print(f"✅ All plots saved to {output_dir}/")


def plot_throughput_comparison(results: List[BenchmarkResult], output_path: Path):
    """Сравнение throughput по типам нагрузки"""
    # Группируем по workload
    workloads = {}
    for r in results:
        if r.name not in workloads:
            workloads[r.name] = {}
        workloads[r.name][r.storage_type] = r.throughput_mbps
    
    # Создаем grouped bar chart
    fig, ax = plt.subplots(figsize=(14, 8))
    
    workload_names = list(workloads.keys())
    storage_types = list(set(r.storage_type for r in results))
    
    x = np.arange(len(workload_names))
    width = 0.25
    
    colors = {'s3fs': '#e74c3c', 'goofys': '#3498db', 'native_s3': '#2ecc71'}
    
    for i, storage in enumerate(storage_types):
        values = [workloads[w].get(storage, 0) for w in workload_names]
        offset = width * (i - len(storage_types)/2 + 0.5)
        bars = ax.bar(x + offset, values, width, 
                     label=storage, color=colors.get(storage, '#95a5a6'))
        
        # Добавляем значения над столбцами
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}',
                       ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Workload Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('Throughput (MB/s)', fontsize=12, fontweight='bold')
    ax.set_title('Sequential Read/Write Throughput Comparison', 
                fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([w.replace('_', '\n') for w in workload_names], fontsize=10)
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {output_path.name}")


def plot_iops_comparison(results: List[BenchmarkResult], output_path: Path):
    """Сравнение IOPS"""
    workloads = {}
    for r in results:
        if r.name not in workloads:
            workloads[r.name] = {}
        workloads[r.name][r.storage_type] = r.iops
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    workload_names = list(workloads.keys())
    storage_types = list(set(r.storage_type for r in results))
    
    x = np.arange(len(workload_names))
    width = 0.25
    
    colors = {'s3fs': '#e74c3c', 'goofys': '#3498db', 'native_s3': '#2ecc71'}
    
    for i, storage in enumerate(storage_types):
        values = [workloads[w].get(storage, 0) for w in workload_names]
        offset = width * (i - len(storage_types)/2 + 0.5)
        bars = ax.bar(x + offset, values, width, 
                     label=storage, color=colors.get(storage, '#95a5a6'))
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}',
                       ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Workload Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('IOPS (operations/sec)', fontsize=12, fontweight='bold')
    ax.set_title('IOPS Performance Comparison', 
                fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([w.replace('_', '\n') for w in workload_names], fontsize=10)
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {output_path.name}")


def plot_latency_percentiles(results: List[BenchmarkResult], output_path: Path):
    """Сравнение latency с перцентилями"""
    # Группируем по storage type
    storage_data = {}
    for r in results:
        if r.storage_type not in storage_data:
            storage_data[r.storage_type] = {'avg': [], 'p95': [], 'p99': []}
        storage_data[r.storage_type]['avg'].append(r.latency_avg_ms)
        storage_data[r.storage_type]['p95'].append(r.latency_p95_ms)
        storage_data[r.storage_type]['p99'].append(r.latency_p99_ms)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    storage_types = list(storage_data.keys())
    x = np.arange(len(storage_types))
    width = 0.25
    
    colors_avg = {'s3fs': '#e74c3c', 'goofys': '#3498db', 'native_s3': '#2ecc71'}
    
    # Средние значения по всем workloads
    avg_values = [np.mean(storage_data[s]['avg']) for s in storage_types]
    p95_values = [np.mean(storage_data[s]['p95']) for s in storage_types]
    p99_values = [np.mean(storage_data[s]['p99']) for s in storage_types]
    
    bars1 = ax.bar(x - width, avg_values, width, label='Average', 
                   color=[colors_avg.get(s, '#95a5a6') for s in storage_types], alpha=0.8)
    bars2 = ax.bar(x, p95_values, width, label='P95',
                   color=[colors_avg.get(s, '#95a5a6') for s in storage_types], alpha=0.6)
    bars3 = ax.bar(x + width, p99_values, width, label='P99',
                   color=[colors_avg.get(s, '#95a5a6') for s in storage_types], alpha=0.4)
    
    # Добавляем значения
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Storage Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Latency Distribution (Average across all workloads)', 
                fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(storage_types, fontsize=11)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {output_path.name}")


def plot_performance_radar(results: List[BenchmarkResult], output_path: Path):
    """Радарный график общей производительности"""
    # Нормализуем метрики для каждого storage type
    storage_types = list(set(r.storage_type for r in results))
    
    # Собираем средние значения
    metrics = {}
    for storage in storage_types:
        storage_results = [r for r in results if r.storage_type == storage]
        metrics[storage] = {
            'Throughput': np.mean([r.throughput_mbps for r in storage_results]),
            'IOPS': np.mean([r.iops for r in storage_results]),
            'Latency\n(lower is better)': 100 - min(100, np.mean([r.latency_avg_ms for r in storage_results])),
        }
    
    # Нормализация к [0, 1]
    normalized = {}
    for metric in ['Throughput', 'IOPS', 'Latency\n(lower is better)']:
        max_val = max(metrics[s][metric] for s in storage_types)
        if max_val > 0:
            for storage in storage_types:
                if storage not in normalized:
                    normalized[storage] = []
                normalized[storage].append(metrics[storage][metric] / max_val)
    
    # Построение радарного графика
    categories = ['Throughput', 'IOPS', 'Latency\n(lower is better)']
    N = len(categories)
    
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    colors = {'s3fs': '#e74c3c', 'goofys': '#3498db', 'native_s3': '#2ecc71'}
    
    for storage in storage_types:
        values = normalized[storage]
        values += values[:1]
        ax.plot(angles, values, 'o-', linewidth=2, 
               label=storage, color=colors.get(storage, '#95a5a6'))
        ax.fill(angles, values, alpha=0.15, color=colors.get(storage, '#95a5a6'))
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    ax.set_title('Overall Performance Comparison (Normalized)', 
                fontsize=14, fontweight='bold', pad=30)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {output_path.name}")

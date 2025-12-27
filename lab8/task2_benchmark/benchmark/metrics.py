"""Сбор и обработка метрик"""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from .base import BenchmarkResult


class MetricsCollector:
    """Сборщик метрик со всех бенчмарков"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_result(self, result: BenchmarkResult):
        """Добавить результат бенчмарка"""
        self.results.append(result)
    
    def save_raw_data(self, output_dir: Path):
        """Сохранить сырые данные в JSON"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            'timestamp': self.timestamp,
            'results': [r.to_dict() for r in self.results]
        }
        
        output_file = output_dir / f"benchmark_raw_{self.timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Raw data saved: {output_file}")
        return output_file
    
    def generate_report(self, output_dir: Path) -> str:
        """Генерация текстового отчета"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("S3 STORAGE BENCHMARK REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Timestamp: {self.timestamp}")
        report_lines.append("")
        
        # Группируем результаты по типу нагрузки
        workloads = {}
        for result in self.results:
            if result.name not in workloads:
                workloads[result.name] = []
            workloads[result.name].append(result)
        
        # Отчет по каждому типу нагрузки
        for workload_name, results in workloads.items():
            report_lines.append(f"\n{'=' * 80}")
            report_lines.append(f"WORKLOAD: {workload_name.upper()}")
            report_lines.append('=' * 80)
            
            for result in results:
                report_lines.append(f"\n  Storage: {result.storage_type}")
                report_lines.append(f"  {'─' * 70}")
                report_lines.append(f"    Throughput:      {result.throughput_mbps:>10.2f} MB/s")
                report_lines.append(f"    IOPS:            {result.iops:>10.2f} ops/s")
                report_lines.append(f"    Latency (avg):   {result.latency_avg_ms:>10.2f} ms")
                report_lines.append(f"    Latency (p95):   {result.latency_p95_ms:>10.2f} ms")
                report_lines.append(f"    Latency (p99):   {result.latency_p99_ms:>10.2f} ms")
                report_lines.append(f"    Total time:      {result.total_time_sec:>10.2f} sec")
                report_lines.append(f"    Errors:          {result.errors:>10}")
            
            # Сравнение
            if len(results) > 1:
                report_lines.append(f"\n  Comparison (Throughput):")
                report_lines.append(f"  {'─' * 70}")
                
                sorted_results = sorted(results, key=lambda x: x.throughput_mbps, reverse=True)
                best = sorted_results[0]
                
                for r in sorted_results:
                    if r.throughput_mbps > 0:
                        ratio = (r.throughput_mbps / best.throughput_mbps) * 100
                        report_lines.append(f"    {r.storage_type:15} {r.throughput_mbps:8.2f} MB/s ({ratio:5.1f}%)")
        
        # Рекомендации
        report_lines.append(f"\n{'=' * 80}")
        report_lines.append("RECOMMENDATIONS")
        report_lines.append('=' * 80)
        report_lines.append("")
        
        # Анализируем лучшие решения для разных сценариев
        recommendations = self._generate_recommendations(workloads)
        report_lines.extend(recommendations)
        
        report_lines.append("\n" + "=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # Сохраняем отчет
        report_file = output_dir / f"benchmark_report_{self.timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"✅ Report saved: {report_file}")
        print("\n" + report_text)
        
        return report_text
    
    def _generate_recommendations(self, workloads: Dict) -> List[str]:
        """Генерация рекомендаций на основе результатов"""
        lines = []
        
        # Находим лучшее решение для каждой нагрузки
        for workload_name, results in workloads.items():
            if not results:
                continue
            
            best = max(results, key=lambda x: x.throughput_mbps)
            
            lines.append(f"• {workload_name}:")
            lines.append(f"    Best: {best.storage_type} ({best.throughput_mbps:.2f} MB/s)")
            
            # Специфичные рекомендации
            if 'sequential' in workload_name.lower():
                lines.append(f"    → Good for: Large file transfers, backups, data lakes")
            elif 'random' in workload_name.lower():
                lines.append(f"    → Good for: Database workloads, random access patterns")
            elif 'small' in workload_name.lower():
                lines.append(f"    → Good for: Many small files, web assets, logs")
            elif 'metadata' in workload_name.lower():
                lines.append(f"    → Good for: File listing, navigation, metadata queries")
            
            lines.append("")
        
        lines.append("General Guidelines:")
        lines.append("  • Native S3 API: Best for programmatic access, highest throughput")
        lines.append("  • goofys: Good balance of performance and POSIX compatibility")
        lines.append("  • s3fs: Most POSIX-compliant, use when compatibility is critical")
        lines.append("")
        
        return lines
    
    def get_results_by_workload(self, workload_name: str) -> List[BenchmarkResult]:
        """Получить результаты для конкретной нагрузки"""
        return [r for r in self.results if r.name == workload_name]
    
    def get_results_by_storage(self, storage_type: str) -> List[BenchmarkResult]:
        """Получить результаты для конкретного типа хранилища"""
        return [r for r in self.results if r.storage_type == storage_type]

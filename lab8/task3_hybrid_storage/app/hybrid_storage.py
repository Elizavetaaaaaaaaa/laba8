"""Менеджер гибридного хранилища"""

import os
import shutil
import time
import hashlib
import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict
from pathlib import Path


class StorageTier(Enum):
    """Уровни хранения"""
    HOT = 'hot'
    WARM = 'warm'
    COLD = 'cold'


@dataclass
class FileMetadata:
    """Метаданные файла"""
    filename: str
    tier: str
    size: int
    created_at: float
    last_accessed: float
    access_count: int
    checksum: str


class HybridStorageManager:
    """Менеджер гибридного хранилища с трехуровневой архитектурой"""
    
    def __init__(self, hot_path: str, warm_path: str, cold_path: str):
        self.paths = {
            StorageTier.HOT: Path(hot_path),
            StorageTier.WARM: Path(warm_path),
            StorageTier.COLD: Path(cold_path)
        }
        self.metadata_file = Path('/tmp/storage_metadata.json')
        self.metadata: Dict[str, FileMetadata] = {}
        self._ensure_dirs()
        self._load_metadata()

    def _ensure_dirs(self):
        """Создание директорий для всех уровней"""
        for tier, path in self.paths.items():
            path.mkdir(parents=True, exist_ok=True)

    def _load_metadata(self):
        """Загрузка метаданных из файла"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.metadata = {
                        k: FileMetadata(**v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"Warning: Could not load metadata: {e}")
                self.metadata = {}

    def _save_metadata(self):
        """Сохранение метаданных в файл"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(
                    {k: asdict(v) for k, v in self.metadata.items()},
                    f,
                    indent=2
                )
        except Exception as e:
            print(f"Warning: Could not save metadata: {e}")

    def put(self, filename: str, data: bytes) -> FileMetadata:
        """Сохранить файл (всегда в HOT tier)"""
        path = self.paths[StorageTier.HOT] / filename
        path.write_bytes(data)

        meta = FileMetadata(
            filename=filename,
            tier=StorageTier.HOT.value,
            size=len(data),
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1,
            checksum=hashlib.md5(data).hexdigest()
        )
        self.metadata[filename] = meta
        self._save_metadata()
        return meta

    def get(self, filename: str) -> Optional[bytes]:
        """Получить файл (с автоматическим promote)"""
        if filename not in self.metadata:
            return None

        meta = self.metadata[filename]
        tier = StorageTier(meta.tier)
        path = self.paths[tier] / filename

        if not path.exists():
            print(f"Warning: File {filename} not found in {tier.value}")
            return None

        # Автоматический promote на HOT при доступе
        if tier != StorageTier.HOT:
            self._promote(filename)
            path = self.paths[StorageTier.HOT] / filename

        meta.last_accessed = time.time()
        meta.access_count += 1
        self._save_metadata()
        
        return path.read_bytes()

    def _promote(self, filename: str):
        """Перемещение файла на уровень выше (promote)"""
        meta = self.metadata[filename]
        current_tier = StorageTier(meta.tier)
        
        if current_tier == StorageTier.HOT:
            return  # Уже на верхнем уровне
        
        target_tier = StorageTier.HOT
        
        src_path = self.paths[current_tier] / filename
        dst_path = self.paths[target_tier] / filename
        
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            src_path.unlink()
            meta.tier = target_tier.value
            self._save_metadata()
            print(f"Promoted {filename}: {current_tier.value} -> {target_tier.value}")

    def _demote(self, filename: str, target_tier: StorageTier):
        """Перемещение файла на уровень ниже (demote)"""
        meta = self.metadata[filename]
        current_tier = StorageTier(meta.tier)
        
        if current_tier == target_tier:
            return
        
        src_path = self.paths[current_tier] / filename
        dst_path = self.paths[target_tier] / filename
        
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            src_path.unlink()
            meta.tier = target_tier.value
            self._save_metadata()
            print(f"Demoted {filename}: {current_tier.value} -> {target_tier.value}")

    def migrate(self):
        """Миграция данных на основе политик"""
        now = time.time()
        migrations = []
        
        for filename, meta in self.metadata.items():
            age_seconds = now - meta.last_accessed
            age_days = age_seconds / 86400
            
            tier = StorageTier(meta.tier)
            
            # HOT -> WARM: 7 дней без доступа
            if tier == StorageTier.HOT and age_days > 7:
                self._demote(filename, StorageTier.WARM)
                migrations.append(f"{filename}: HOT -> WARM (age: {age_days:.1f} days)")
            
            # WARM -> COLD: 30 дней без доступа
            elif tier == StorageTier.WARM and age_days > 30:
                self._demote(filename, StorageTier.COLD)
                migrations.append(f"{filename}: WARM -> COLD (age: {age_days:.1f} days)")
        
        return migrations

    def status(self) -> Dict:
        """Получить статус хранилища"""
        stats = {
            'hot': {'count': 0, 'size': 0},
            'warm': {'count': 0, 'size': 0},
            'cold': {'count': 0, 'size': 0},
            'total': {'count': 0, 'size': 0}
        }
        
        for filename, meta in self.metadata.items():
            tier = meta.tier
            stats[tier]['count'] += 1
            stats[tier]['size'] += meta.size
            stats['total']['count'] += 1
            stats['total']['size'] += meta.size
        
        return stats

    def list_files(self) -> list:
        """Список всех файлов"""
        return [
            {
                'filename': meta.filename,
                'tier': meta.tier,
                'size': meta.size,
                'access_count': meta.access_count,
                'last_accessed': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(meta.last_accessed))
            }
            for meta in self.metadata.values()
        ]

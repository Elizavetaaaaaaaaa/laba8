"""CLI для демонстрации гибридного хранилища"""

import sys
from hybrid_storage import HybridStorageManager


def format_size(size_bytes):
    """Форматирование размера в человекочитаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def print_banner():
    """Печать заголовка"""
    print("=" * 60)
    print("  Hybrid Storage Manager - TechData Solutions")
    print("  HOT (Local SSD) | WARM (S3FS/MinIO) | COLD (Archive)")
    print("=" * 60)


def main():
    """Основной цикл CLI"""
    # Инициализация менеджера
    manager = HybridStorageManager(
        hot_path='/data/hot',
        warm_path='/data/warm',
        cold_path='/tmp/cold'  # COLD tier - симуляция
    )
    
    print_banner()
    print("\nCommands: put <filename> <content> | get <filename> | status | list | migrate | help | exit")
    print()
    
    while True:
        try:
            cmd = input("> ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split(maxsplit=2)
            command = parts[0].lower()
            
            if command == 'exit':
                print("Goodbye!")
                break
            
            elif command == 'help':
                print("\nAvailable commands:")
                print("  put <filename> <content>  - Save file to HOT tier")
                print("  get <filename>            - Retrieve file (auto-promote to HOT)")
                print("  status                    - Show storage statistics")
                print("  list                      - List all files")
                print("  migrate                   - Run migration policy")
                print("  help                      - Show this help")
                print("  exit                      - Exit application")
                print()
            
            elif command == 'put':
                if len(parts) < 3:
                    print("Usage: put <filename> <content>")
                    continue
                
                filename = parts[1]
                content = parts[2]
                
                meta = manager.put(filename, content.encode('utf-8'))
                print(f"✓ Saved '{filename}' to {meta.tier} tier ({meta.size} bytes)")
            
            elif command == 'get':
                if len(parts) < 2:
                    print("Usage: get <filename>")
                    continue
                
                filename = parts[1]
                data = manager.get(filename)
                
                if data is None:
                    print(f"✗ File '{filename}' not found")
                else:
                    print(f"✓ Retrieved '{filename}':")
                    print(f"  Content: {data.decode('utf-8')}")
                    print(f"  Size: {len(data)} bytes")
            
            elif command == 'status':
                stats = manager.status()
                
                print("\n" + "=" * 60)
                print("Storage Status:")
                print("=" * 60)
                
                for tier in ['hot', 'warm', 'cold']:
                    count = stats[tier]['count']
                    size = stats[tier]['size']
                    print(f"  {tier.upper():6} | Files: {count:4} | Size: {format_size(size):>12}")
                
                print("-" * 60)
                total_count = stats['total']['count']
                total_size = stats['total']['size']
                print(f"  TOTAL  | Files: {total_count:4} | Size: {format_size(total_size):>12}")
                print("=" * 60 + "\n")
            
            elif command == 'list':
                files = manager.list_files()
                
                if not files:
                    print("No files in storage")
                    continue
                
                print("\n" + "=" * 80)
                print(f"{'Filename':<20} {'Tier':<6} {'Size':<10} {'Access':<8} {'Last Accessed':<20}")
                print("=" * 80)
                
                for f in files:
                    print(f"{f['filename']:<20} {f['tier']:<6} {format_size(f['size']):<10} "
                          f"{f['access_count']:<8} {f['last_accessed']:<20}")
                
                print("=" * 80 + "\n")
            
            elif command == 'migrate':
                print("Running migration policy...")
                migrations = manager.migrate()
                
                if migrations:
                    print(f"\n✓ Migrated {len(migrations)} files:")
                    for m in migrations:
                        print(f"  - {m}")
                else:
                    print("✓ No files need migration")
                print()
            
            else:
                print(f"Unknown command: {command}")
                print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    main()

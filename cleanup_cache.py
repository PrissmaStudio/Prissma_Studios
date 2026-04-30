#!/usr/bin/env python3
"""
Cleanup cache - remove old/unused photo thumbnails
Keeps only cache for galleries with active reviews
"""

import os
import shutil
import sqlite3
from pathlib import Path
from collections import defaultdict

# Paths
PROJECT_ROOT = '/Users/alex/Desktop/Prissma'
DB_PATH = os.path.join(PROJECT_ROOT, 'instance', 'prissma.db')
CACHE_THUMBS_PATH = os.path.join(PROJECT_ROOT, 'misc_data', 'cache_thumbs')
CACHE_PATH = os.path.join(PROJECT_ROOT, 'misc_data', 'cache')

def get_active_folders():
    """Get list of folders that have reviews in database"""
    if not os.path.exists(DB_PATH):
        print("❌ Database not found")
        return set()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT folder FROM review WHERE folder IS NOT NULL")
        folders = set(row[0] for row in cursor.fetchall() if row[0])
        conn.close()
        
        print(f"✅ Found {len(folders)} active folders in database:")
        for folder in sorted(folders):
            print(f"   - {folder}")
        return folders
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return set()

def count_files_in_folder(path):
    """Count all files recursively in a folder"""
    try:
        return sum(1 for _ in Path(path).rglob('*') if _.is_file())
    except:
        return 0

def get_folder_size_mb(path):
    """Get total size of folder in MB"""
    try:
        total_size = sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())
        return total_size / (1024 * 1024)  # Convert to MB
    except:
        return 0


def cleanup_old_variants(active_folder):
    """Remove old thumbnail variants that are no longer used."""
    removed = []
    old_suffixes = ('.grid-xs.', '.grid-sm.', '.grid-md.')
    for root, _, files in os.walk(active_folder):
        for name in files:
            lower_name = name.lower()
            if any(suffix in lower_name for suffix in old_suffixes):
                removed.append(os.path.join(root, name))
    for path in removed:
        try:
            os.remove(path)
        except Exception:
            pass
    return removed


def cleanup_cache():
    """Remove cache for inactive folders"""
    print("\n🧹 Analyzing cache...\n")
    
    if not os.path.exists(CACHE_THUMBS_PATH):
        print(f"❌ Cache directory not found: {CACHE_THUMBS_PATH}")
        return
    
    active_folders = get_active_folders()
    
    # Analyze current cache
    cache_folders = [d for d in os.listdir(CACHE_THUMBS_PATH) 
                     if os.path.isdir(os.path.join(CACHE_THUMBS_PATH, d)) and d != '.DS_Store']
    
    print(f"\n📊 Current cache contents ({len(cache_folders)} folders):\n")
    
    total_files = 0
    total_size_mb = 0
    to_delete = []
    to_keep = []
    
    for folder in sorted(cache_folders):
        folder_path = os.path.join(CACHE_THUMBS_PATH, folder)
        file_count = count_files_in_folder(folder_path)
        folder_size_mb = get_folder_size_mb(folder_path)
        
        total_files += file_count
        total_size_mb += folder_size_mb
        
        if folder in active_folders:
            status = "✅ KEEP"
            to_keep.append((folder, file_count, folder_size_mb))
        else:
            status = "❌ DELETE"
            to_delete.append((folder, file_count, folder_size_mb, folder_path))
        
        print(f"{status}  {folder:<30} {file_count:>6} files  {folder_size_mb:>8.2f} MB")
    
    print(f"\n📈 TOTAL: {total_files} files, {total_size_mb:.2f} MB")
    
    if not to_delete:
        print("\n✅ Cache is clean! No old folders to delete.")
        return
    
    # Show what will be deleted
    print(f"\n🗑️  Will delete {len(to_delete)} inactive folders:\n")
    delete_files = 0
    delete_size_mb = 0
    
    for folder, file_count, folder_size_mb, folder_path in to_delete:
        delete_files += file_count
        delete_size_mb += folder_size_mb
        print(f"   - {folder:<30} {file_count:>6} files  {folder_size_mb:>8.2f} MB")
    
    print(f"\n📉 Total to delete: {delete_files} files, {delete_size_mb:.2f} MB")
    print(f"💾 Space saved: {delete_size_mb:.2f} MB ({(delete_size_mb/total_size_mb*100):.1f}% reduction)")
    
    # Confirm and delete
    response = input("\n🤔 Delete inactive cache folders? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print("\n🗑️  Deleting...\n")
        for folder, file_count, folder_size_mb, folder_path in to_delete:
            try:
                shutil.rmtree(folder_path)
                print(f"✅ Deleted {folder}")
            except Exception as e:
                print(f"❌ Failed to delete {folder}: {e}")
        
        # Also clean up the generic cache (Flask cache)
        if os.path.exists(CACHE_PATH):
            try:
                shutil.rmtree(CACHE_PATH)
                os.makedirs(CACHE_PATH, exist_ok=True)
                print(f"✅ Cleared Flask cache directory")
            except Exception as e:
                print(f"⚠️  Could not clear Flask cache: {e}")

        print(f"\n🎉 Cleanup complete! Freed up ~{delete_size_mb:.2f} MB")

        # Remove old variant files from active cache folders too
        if active_folders:
            resp = input("\n🧹 Purge old grid variants from active cache folders too? (yes/no): ").strip().lower()
            if resp in ['yes', 'y']:
                old_removed = 0
                for folder in sorted(active_folders):
                    folder_path = os.path.join(CACHE_THUMBS_PATH, folder)
                    if not os.path.isdir(folder_path):
                        continue
                    removed = cleanup_old_variants(folder_path)
                    if removed:
                        print(f"✅ Purged {len(removed)} old variants from {folder}")
                        old_removed += len(removed)
                if old_removed:
                    print(f"\n🎉 Removed {old_removed} old variant files from active cache")
                else:
                    print("\n✅ No old variant files found in active cache folders")
            else:
                print("\n⏭️  Skipped active cache variant cleanup.")
    else:
        print("\n⏭️  Cleanup cancelled.")

if __name__ == '__main__':
    cleanup_cache()

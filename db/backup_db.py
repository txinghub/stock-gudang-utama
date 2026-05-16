#!/usr/bin/env python3
"""
Auto-backup script for stock-gudang-utama
Backup sebelum perubahan, simpan ke local + NAS
"""
import sqlite3
import shutil
import os
import glob
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'stock.db')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')
NAS_DIR = '/Users/linggothioputro/NAS_Hermes/stock-gudang-utama/backups'
MAX_LOCAL_BACKUPS = 10

def get_db_path():
    return DB_PATH

def backup_local():
    """Backup ke folder backups lokal"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_DIR, f'stock_{ts}.db')
    shutil.copy2(DB_PATH, dest)
    
    # Keep only MAX_LOCAL_BACKUPS newest
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'stock_*.db')))
    while len(backups) > MAX_LOCAL_BACKUPS:
        os.remove(backups.pop(0))
    
    return dest

def backup_nas():
    """Backup ke NAS jika tersedia"""
    try:
        os.makedirs(NAS_DIR, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = os.path.join(NAS_DIR, f'stock_{ts}.db')
        shutil.copy2(DB_PATH, dest)
        return dest
    except Exception as e:
        print(f"NAS backup failed: {e}")
        return None

def restore_from_backup(backup_path):
    """Restore database dari backup"""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    shutil.copy2(backup_path, DB_PATH)
    return True

def list_backups():
    """List semua backup yang ada"""
    local = sorted(glob.glob(os.path.join(BACKUP_DIR, 'stock_*.db')), reverse=True)
    nas = sorted(glob.glob(os.path.join(NAS_DIR, 'stock_*.db')), reverse=True)
    return {'local': local, 'nas': nas}

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'restore' and len(sys.argv) > 2:
        restore_from_backup(sys.argv[2])
        print(f"Restored from {sys.argv[2]}")
    else:
        lb = backup_local()
        nb = backup_nas()
        print(f"Local: {lb}")
        print(f"NAS: {nb}")
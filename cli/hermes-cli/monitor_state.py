"""Monitor state management for file tracking and duplicate detection"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import fcntl


STATE_DIR = Path.home() / '.hermes'
STATE_FILE = STATE_DIR / 'monitor-state.json'
BACKUP_COUNT = 5
RETENTION_DAYS = 30


class MonitorStateManager:
    """Manages monitor state including processed files tracking"""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or STATE_FILE
        self.state_file.parent.mkdir(mode=0o700, exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file"""
        if not self.state_file.exists():
            return {
                'processed_files': {},
                'stats': {
                    'total_processed': 0,
                    'total_errors': 0,
                    'last_processed_at': None
                }
            }

        try:
            with open(self.state_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    state = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return state
        except (json.JSONDecodeError, IOError):
            # Recreate if corrupted
            return {
                'processed_files': {},
                'stats': {
                    'total_processed': 0,
                    'total_errors': 0,
                    'last_processed_at': None
                }
            }

    def _save_state(self):
        """Save state to file with file locking"""
        # Backup existing state
        if self.state_file.exists() and self.state_file.stat().st_size > 0:
            self._backup_state()

        # Write new state
        with open(self.state_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(self._state, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _backup_state(self):
        """Create timestamped backup of state file"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_file = self.state_file.parent / f'monitor-state.{timestamp}.json.bak'

        # Copy current state to backup
        import shutil
        shutil.copy2(self.state_file, backup_file)

        # Clean old backups
        backups = sorted(self.state_file.parent.glob('monitor-state.*.json.bak'))
        if len(backups) > BACKUP_COUNT:
            for old_backup in backups[:-BACKUP_COUNT]:
                old_backup.unlink()

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file content"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def is_duplicate(self, file_path: str) -> bool:
        """Check if file has already been processed"""
        try:
            current_hash = self.calculate_file_hash(file_path)
            processed_files = self._state.get('processed_files', {})

            # Check if any processed file has the same hash
            for entry in processed_files.values():
                if entry.get('hash') == current_hash:
                    return True

            return False
        except (IOError, OSError):
            # If we can't read the file, treat as not duplicate
            return False

    def mark_processed(self, file_path: str, scan_id: str, host_count: int = 0,
                       service_count: int = 0):
        """Mark a file as processed"""
        try:
            file_hash = self.calculate_file_hash(file_path)
            timestamp = datetime.now().isoformat()

            self._state['processed_files'][file_path] = {
                'hash': file_hash,
                'processed_at': timestamp,
                'scan_id': scan_id,
                'host_count': host_count,
                'service_count': service_count
            }

            # Update stats
            self._state['stats']['total_processed'] += 1
            self._state['stats']['last_processed_at'] = timestamp

            self._save_state()
        except (IOError, OSError):
            # If we can't hash/save, just continue
            pass

    def mark_error(self, file_path: str, error: str):
        """Mark a file processing error"""
        self._state['stats']['total_errors'] += 1
        self._save_state()

    def cleanup_old_entries(self, days: int = RETENTION_DAYS):
        """Remove entries older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        processed_files = self._state.get('processed_files', {})

        # Find old entries
        to_remove = []
        for file_path, entry in processed_files.items():
            processed_at = entry.get('processed_at')
            if processed_at:
                try:
                    processed_date = datetime.fromisoformat(processed_at)
                    if processed_date < cutoff_date:
                        to_remove.append(file_path)
                except ValueError:
                    # Invalid date format, remove it
                    to_remove.append(file_path)

        # Remove old entries
        for file_path in to_remove:
            del processed_files[file_path]

        if to_remove:
            self._save_state()

        return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self._state.get('stats', {})

    def get_processed_count(self) -> int:
        """Get count of processed files"""
        return len(self._state.get('processed_files', {}))

#!/usr/bin/env python3

"""
Daemon management for Hermes monitor
"""

import os
import sys
import signal
import json
import daemon
from daemon import pidfile
from pathlib import Path
from typing import Optional


class MonitorDaemon:
    """Manages monitor daemon lifecycle"""

    def __init__(self, hermes_dir: str = "~/.hermes"):
        self.hermes_dir = os.path.expanduser(hermes_dir)
        self.pid_file = os.path.join(self.hermes_dir, "monitor.pid")
        self.log_file = os.path.join(self.hermes_dir, "monitor.log")
        self.state_file = os.path.join(self.hermes_dir, "daemon-state.json")

        # Ensure directory exists
        os.makedirs(self.hermes_dir, exist_ok=True)

    def is_running(self) -> bool:
        """Check if daemon is currently running"""
        if not os.path.exists(self.pid_file):
            return False

        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            # PID file exists but process doesn't
            self._cleanup_pid_file()
            return False

    def get_pid(self) -> Optional[int]:
        """Get PID of running daemon"""
        if not os.path.exists(self.pid_file):
            return None

        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None

    def _cleanup_pid_file(self):
        """Remove stale PID file"""
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    def start(self, config_path: str, run_function):
        """Start the daemon"""
        if self.is_running():
            raise RuntimeError(f"Monitor daemon is already running (PID: {self.get_pid()})")

        # Save config path to state
        self._save_state({'config_path': config_path})

        # Create daemon context
        context = daemon.DaemonContext(
            working_directory=os.getcwd(),
            pidfile=pidfile.TimeoutPIDLockFile(self.pid_file),
            umask=0o002,
            detach_process=True,
            stdout=open(self.log_file, 'a'),
            stderr=open(self.log_file, 'a'),
            signal_map={
                signal.SIGTERM: self._shutdown_handler,
                signal.SIGHUP: self._reload_handler,
            }
        )

        # Start daemon
        with context:
            run_function(config_path)

    def stop(self) -> bool:
        """Stop the daemon"""
        pid = self.get_pid()
        if pid is None:
            return False

        try:
            # Send SIGTERM
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit (with timeout)
            import time
            for _ in range(30):  # 30 second timeout
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except ProcessLookupError:
                    # Process exited
                    self._cleanup_pid_file()
                    return True

            # Force kill if still running
            os.kill(pid, signal.SIGKILL)
            self._cleanup_pid_file()
            return True

        except ProcessLookupError:
            self._cleanup_pid_file()
            return False
        except PermissionError:
            raise RuntimeError("Permission denied to stop daemon")

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signal"""
        sys.exit(0)

    def _reload_handler(self, signum, frame):
        """Handle reload signal (log rotation)"""
        # Reopen log files
        pass

    def _save_state(self, state: dict):
        """Save daemon state"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f)

    def load_state(self) -> dict:
        """Load daemon state"""
        if not os.path.exists(self.state_file):
            return {}

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def get_status(self) -> dict:
        """Get daemon status information"""
        pid = self.get_pid()
        state = self.load_state()

        return {
            'running': self.is_running(),
            'pid': pid,
            'config_path': state.get('config_path'),
            'log_file': self.log_file if os.path.exists(self.log_file) else None
        }

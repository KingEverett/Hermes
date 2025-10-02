#!/usr/bin/env python3

"""
Tests for monitor daemon and multi-directory functionality
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from monitor_config import MonitorConfig, MonitorConfigFile
from monitor_daemon import MonitorDaemon


class TestMonitorConfig:
    """Test MonitorConfig dataclass"""

    def test_create_monitor_config(self):
        """Test creating a monitor configuration"""
        config = MonitorConfig(
            directory="~/scans",
            project="test-project",
            patterns=["*.xml", "*.json"]
        )

        assert config.directory == os.path.expanduser("~/scans")
        assert config.project == "test-project"
        assert config.patterns == ["*.xml", "*.json"]
        assert config.delay == 5  # default
        assert config.max_concurrent == 3  # default
        assert config.exclude is not None

    def test_monitor_config_to_dict(self):
        """Test converting config to dictionary"""
        config = MonitorConfig(
            directory="/tmp/scans",
            project="test",
            patterns=["*.xml"],
            delay=10
        )

        data = config.to_dict()
        assert data['directory'] == "/tmp/scans"
        assert data['project'] == "test"
        assert data['patterns'] == ["*.xml"]
        assert data['delay'] == 10

    def test_monitor_config_from_dict(self):
        """Test creating config from dictionary"""
        data = {
            'directory': '/tmp/test',
            'project': 'my-project',
            'patterns': ['*.json'],
            'recursive': True,
            'delay': 7
        }

        config = MonitorConfig.from_dict(data)
        assert config.directory == '/tmp/test'
        assert config.project == 'my-project'
        assert config.recursive is True
        assert config.delay == 7


class TestMonitorConfigFile:
    """Test MonitorConfigFile"""

    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration file"""
        config_file = tmp_path / "monitor.json"
        config_mgr = MonitorConfigFile(str(config_file))

        # Create configs
        configs = [
            MonitorConfig(
                directory=str(tmp_path / "scan1"),
                project="project1",
                patterns=["*.xml"]
            ),
            MonitorConfig(
                directory=str(tmp_path / "scan2"),
                project="project2",
                patterns=["*.json"],
                delay=10
            )
        ]

        # Save
        config_mgr.save(configs)
        assert config_file.exists()

        # Load
        loaded = config_mgr.load()
        assert len(loaded) == 2
        assert loaded[0].project == "project1"
        assert loaded[1].delay == 10

    def test_load_array_format(self, tmp_path):
        """Test loading config file with array format"""
        config_file = tmp_path / "monitor.json"

        # Write array format directly
        data = [
            {
                'directory': str(tmp_path / "test"),
                'project': 'test-project',
                'patterns': ['*.xml'],
                'recursive': False,
                'delay': 5,
                'max_concurrent': 3
            }
        ]

        with open(config_file, 'w') as f:
            json.dump(data, f)

        # Load
        config_mgr = MonitorConfigFile(str(config_file))
        loaded = config_mgr.load()

        assert len(loaded) == 1
        assert loaded[0].project == "test-project"

    def test_load_object_format(self, tmp_path):
        """Test loading config file with object format"""
        config_file = tmp_path / "monitor.json"

        # Write object format
        data = {
            'monitors': [
                {
                    'directory': str(tmp_path / "test"),
                    'project': 'test-project',
                    'patterns': ['*.xml'],
                    'recursive': False,
                    'delay': 5,
                    'max_concurrent': 3
                }
            ]
        }

        with open(config_file, 'w') as f:
            json.dump(data, f)

        # Load
        config_mgr = MonitorConfigFile(str(config_file))
        loaded = config_mgr.load()

        assert len(loaded) == 1
        assert loaded[0].project == "test-project"

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading non-existent config file raises error"""
        config_file = tmp_path / "nonexistent.json"
        config_mgr = MonitorConfigFile(str(config_file))

        with pytest.raises(FileNotFoundError):
            config_mgr.load()

    def test_create_example_config(self, tmp_path):
        """Test creating example configuration file"""
        config_file = tmp_path / "example.json"

        MonitorConfigFile.create_example(str(config_file))

        assert config_file.exists()

        # Load and verify
        with open(config_file, 'r') as f:
            data = json.load(f)

        assert 'monitors' in data
        assert len(data['monitors']) == 2
        assert data['monitors'][0]['directory'] == '~/scans/nmap'


class TestMonitorDaemon:
    """Test MonitorDaemon"""

    def test_daemon_initialization(self, tmp_path):
        """Test daemon initialization"""
        hermes_dir = str(tmp_path / ".hermes")
        daemon = MonitorDaemon(hermes_dir)

        assert daemon.hermes_dir == hermes_dir
        assert daemon.pid_file == os.path.join(hermes_dir, "monitor.pid")
        assert daemon.log_file == os.path.join(hermes_dir, "monitor.log")
        assert os.path.exists(hermes_dir)

    def test_is_running_no_pid_file(self, tmp_path):
        """Test is_running when no PID file exists"""
        hermes_dir = str(tmp_path / ".hermes")
        daemon = MonitorDaemon(hermes_dir)

        assert daemon.is_running() is False

    def test_is_running_with_stale_pid(self, tmp_path):
        """Test is_running with stale PID file"""
        hermes_dir = str(tmp_path / ".hermes")
        daemon = MonitorDaemon(hermes_dir)

        # Create PID file with non-existent PID
        with open(daemon.pid_file, 'w') as f:
            f.write("999999")

        # Should return False and cleanup
        assert daemon.is_running() is False
        assert not os.path.exists(daemon.pid_file)

    def test_get_pid(self, tmp_path):
        """Test getting PID from file"""
        hermes_dir = str(tmp_path / ".hermes")
        daemon = MonitorDaemon(hermes_dir)

        # No PID file
        assert daemon.get_pid() is None

        # Create PID file
        with open(daemon.pid_file, 'w') as f:
            f.write("12345")

        assert daemon.get_pid() == 12345

    def test_save_and_load_state(self, tmp_path):
        """Test state persistence"""
        hermes_dir = str(tmp_path / ".hermes")
        daemon = MonitorDaemon(hermes_dir)

        # Save state
        state = {'config_path': '/tmp/config.json', 'monitors': 3}
        daemon._save_state(state)

        # Load state
        loaded = daemon.load_state()
        assert loaded == state

    def test_get_status_not_running(self, tmp_path):
        """Test getting status when daemon is not running"""
        hermes_dir = str(tmp_path / ".hermes")
        daemon = MonitorDaemon(hermes_dir)

        status = daemon.get_status()

        assert status['running'] is False
        assert status['pid'] is None
        assert status['log_file'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

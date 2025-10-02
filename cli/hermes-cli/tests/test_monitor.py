"""Unit tests for monitor command"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
import json

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes import cli, ScanFileHandler
from monitor_state import MonitorStateManager
from api_client import HermesAPIClient


class TestFilePatternMatching:
    """Test file pattern matching logic"""

    def test_matches_xml_pattern(self):
        """Test that XML files match *.xml pattern"""
        handler = ScanFileHandler(
            project_id="test",
            api_client=Mock(),
            patterns=["*.xml"],
            exclude_patterns=[],
            delay=0,
            state_manager=Mock()
        )
        assert handler._should_process("/path/to/scan.xml")

    def test_matches_multiple_patterns(self):
        """Test matching against multiple patterns"""
        handler = ScanFileHandler(
            project_id="test",
            api_client=Mock(),
            patterns=["*.xml", "*.json"],
            exclude_patterns=[],
            delay=0,
            state_manager=Mock()
        )
        assert handler._should_process("/path/to/scan.xml")
        assert handler._should_process("/path/to/scan.json")
        assert not handler._should_process("/path/to/scan.txt")

    def test_exclusion_patterns(self):
        """Test that exclusion patterns work"""
        handler = ScanFileHandler(
            project_id="test",
            api_client=Mock(),
            patterns=["*.xml"],
            exclude_patterns=["*.tmp", "*~"],
            delay=0,
            state_manager=Mock()
        )
        assert handler._should_process("/path/to/scan.xml")
        assert not handler._should_process("/path/to/scan.xml.tmp")
        assert not handler._should_process("/path/to/scan.xml~")

    def test_case_sensitive_matching(self):
        """Test that matching is case-sensitive by default"""
        handler = ScanFileHandler(
            project_id="test",
            api_client=Mock(),
            patterns=["*.xml"],
            exclude_patterns=[],
            delay=0,
            state_manager=Mock()
        )
        assert handler._should_process("/path/to/scan.xml")
        # Note: fnmatch on Linux is case-sensitive
        assert not handler._should_process("/path/to/scan.XML")

    def test_complex_glob_patterns(self):
        """Test complex glob patterns like *nmap*.xml"""
        handler = ScanFileHandler(
            project_id="test",
            api_client=Mock(),
            patterns=["*nmap*.xml", "*masscan*.json"],
            exclude_patterns=[],
            delay=0,
            state_manager=Mock()
        )
        assert handler._should_process("/path/to/nmap-scan.xml")
        assert handler._should_process("/path/to/scan-nmap.xml")
        assert handler._should_process("/path/to/masscan-results.json")
        assert not handler._should_process("/path/to/scan.xml")


class TestMonitorStateManager:
    """Test monitor state management"""

    def test_initial_state_creation(self, tmp_path):
        """Test that initial state is created correctly"""
        state_file = tmp_path / "state.json"
        manager = MonitorStateManager(state_file)

        assert manager._state['processed_files'] == {}
        assert manager._state['stats']['total_processed'] == 0
        assert manager._state['stats']['total_errors'] == 0

    def test_file_hash_calculation(self, tmp_path):
        """Test file hash calculation"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = MonitorStateManager(tmp_path / "state.json")
        hash1 = manager.calculate_file_hash(str(test_file))

        # Hash should be consistent
        hash2 = manager.calculate_file_hash(str(test_file))
        assert hash1 == hash2

        # Different content should produce different hash
        test_file.write_text("different content")
        hash3 = manager.calculate_file_hash(str(test_file))
        assert hash1 != hash3

    def test_duplicate_detection(self, tmp_path):
        """Test duplicate file detection"""
        state_file = tmp_path / "state.json"
        manager = MonitorStateManager(state_file)

        test_file = tmp_path / "scan.xml"
        test_file.write_text("<nmaprun></nmaprun>")

        # First time should not be duplicate
        assert not manager.is_duplicate(str(test_file))

        # Mark as processed
        manager.mark_processed(str(test_file), "scan-id-123")

        # Second time should be duplicate
        assert manager.is_duplicate(str(test_file))

    def test_duplicate_detection_different_path_same_content(self, tmp_path):
        """Test that duplicate detection works for same content, different path"""
        state_file = tmp_path / "state.json"
        manager = MonitorStateManager(state_file)

        file1 = tmp_path / "scan1.xml"
        file2 = tmp_path / "scan2.xml"

        # Same content
        content = "<nmaprun><host>test</host></nmaprun>"
        file1.write_text(content)
        file2.write_text(content)

        # Process first file
        manager.mark_processed(str(file1), "scan-id-1")

        # Second file with same content should be detected as duplicate
        assert manager.is_duplicate(str(file2))

    def test_mark_processed_updates_stats(self, tmp_path):
        """Test that marking files as processed updates stats"""
        state_file = tmp_path / "state.json"
        manager = MonitorStateManager(state_file)

        test_file = tmp_path / "scan.xml"
        test_file.write_text("<nmaprun></nmaprun>")

        initial_count = manager._state['stats']['total_processed']
        manager.mark_processed(str(test_file), "scan-id-123", 10, 50)

        assert manager._state['stats']['total_processed'] == initial_count + 1
        assert str(test_file) in manager._state['processed_files']
        assert manager._state['processed_files'][str(test_file)]['scan_id'] == "scan-id-123"
        assert manager._state['processed_files'][str(test_file)]['host_count'] == 10
        assert manager._state['processed_files'][str(test_file)]['service_count'] == 50

    def test_mark_error_updates_stats(self, tmp_path):
        """Test that marking errors updates stats"""
        state_file = tmp_path / "state.json"
        manager = MonitorStateManager(state_file)

        initial_errors = manager._state['stats']['total_errors']
        manager.mark_error("/path/to/file.xml", "Test error")

        assert manager._state['stats']['total_errors'] == initial_errors + 1

    def test_state_persistence(self, tmp_path):
        """Test that state is persisted across instances"""
        state_file = tmp_path / "state.json"

        # Create manager and add data
        manager1 = MonitorStateManager(state_file)
        test_file = tmp_path / "scan.xml"
        test_file.write_text("<nmaprun></nmaprun>")
        manager1.mark_processed(str(test_file), "scan-id-123")

        # Create new manager instance
        manager2 = MonitorStateManager(state_file)

        # Data should be persisted
        assert manager2.is_duplicate(str(test_file))
        assert manager2._state['stats']['total_processed'] == 1

    def test_cleanup_old_entries(self, tmp_path):
        """Test cleanup of old state entries"""
        from datetime import datetime, timedelta

        state_file = tmp_path / "state.json"
        manager = MonitorStateManager(state_file)

        # Add old entry manually
        old_date = (datetime.now() - timedelta(days=35)).isoformat()
        manager._state['processed_files']['/old/file.xml'] = {
            'hash': 'oldhash',
            'processed_at': old_date,
            'scan_id': 'old-id'
        }

        # Add recent entry
        test_file = tmp_path / "scan.xml"
        test_file.write_text("<nmaprun></nmaprun>")
        manager.mark_processed(str(test_file), "new-id")

        # Cleanup
        removed = manager.cleanup_old_entries(days=30)

        assert removed == 1
        assert '/old/file.xml' not in manager._state['processed_files']
        assert str(test_file) in manager._state['processed_files']


class TestMonitorCommand:
    """Test monitor CLI command"""

    @patch('hermes.Observer')
    @patch('hermes.get_api_client')
    @patch('hermes.time.sleep')
    def test_monitor_command_basic(self, mock_sleep, mock_get_client, mock_observer_class, tmp_path):
        """Test basic monitor command execution"""
        runner = CliRunner()

        # Mock API client
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock observer - is_alive will be called in the while loop
        mock_observer = Mock()
        # First call returns True (enter loop), subsequent calls return False (exit loop)
        mock_observer.is_alive.side_effect = [True, False]
        mock_observer_class.return_value = mock_observer

        # Mock sleep to prevent actual waiting
        mock_sleep.return_value = None

        # Set test environment variable
        with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_monitor_command_basic'}):
            result = runner.invoke(cli, [
                'monitor', 'run',
                str(tmp_path),
                '--project', 'test-project',
                '--delay', '1'
            ], catch_exceptions=False)

        # Check that observer was created and started
        assert mock_observer.start.called
        assert mock_observer.schedule.called
        assert result.exit_code == 0

    def test_monitor_command_requires_project(self, tmp_path):
        """Test that monitor command requires --project option"""
        runner = CliRunner()

        result = runner.invoke(cli, ['monitor', 'run', str(tmp_path)])

        assert result.exit_code != 0
        assert 'project' in result.output.lower() or 'required' in result.output.lower()

    def test_monitor_command_requires_directory(self):
        """Test that monitor command requires directory argument"""
        runner = CliRunner()

        result = runner.invoke(cli, ['monitor', 'run', '--project', 'test'])

        assert result.exit_code != 0

    @patch('hermes.time.sleep')
    def test_monitor_command_pattern_parsing(self, mock_sleep, tmp_path):
        """Test that patterns are correctly parsed"""
        runner = CliRunner()

        with patch('hermes.Observer') as mock_observer_class, \
             patch('hermes.get_api_client'):

            # Mock observer to exit immediately
            mock_observer = Mock()
            mock_observer.is_alive.side_effect = [True, False]
            mock_observer_class.return_value = mock_observer

            # Mock sleep to prevent waiting
            mock_sleep.return_value = None

            with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_monitor_command_pattern_parsing'}):
                result = runner.invoke(cli, [
                    'monitor', 'run',
                    str(tmp_path),
                    '--project', 'test',
                    '--patterns', '*.xml,*.json,*.txt'
                ], catch_exceptions=False)

            # Command should accept the patterns without error
            assert 'invalid' not in result.output.lower()
            assert result.exit_code == 0


class TestScanFileHandler:
    """Test ScanFileHandler event handling"""

    def test_handler_processes_matching_files(self, tmp_path):
        """Test that handler processes files matching patterns"""
        # Mock API client and state manager
        mock_client = Mock()
        mock_client.import_scan.return_value = {
            'scan_id': 'test-id',
            'host_count': 5,
            'service_count': 10,
            'status': 'completed'
        }

        mock_state = Mock()
        mock_state.is_duplicate.return_value = False

        handler = ScanFileHandler(
            project_id="test",
            api_client=mock_client,
            patterns=["*.xml"],
            exclude_patterns=[],
            delay=0,  # No delay for testing
            state_manager=mock_state
        )

        # Create test file
        test_file = tmp_path / "scan.xml"
        test_file.write_text("<nmaprun></nmaprun>")

        # Simulate file creation event
        event = Mock()
        event.is_directory = False
        event.src_path = str(test_file)

        handler.on_created(event)

        # Give a moment for timer to execute and submit to executor
        time.sleep(0.2)

        # Shutdown handler to wait for executor tasks
        handler.shutdown(timeout=1)

        # Check that file was processed
        assert mock_client.import_scan.called

    def test_handler_skips_excluded_files(self, tmp_path):
        """Test that handler skips files matching exclusion patterns"""
        mock_client = Mock()
        mock_state = Mock()

        handler = ScanFileHandler(
            project_id="test",
            api_client=mock_client,
            patterns=["*.xml"],
            exclude_patterns=["*.tmp"],
            delay=0,
            state_manager=mock_state
        )

        # Create excluded file
        test_file = tmp_path / "scan.xml.tmp"
        test_file.write_text("content")

        # Simulate file creation event
        event = Mock()
        event.is_directory = False
        event.src_path = str(test_file)

        handler.on_created(event)

        # Should not be in pending timers
        assert str(test_file) not in handler.pending_timers

        # Cleanup
        handler.shutdown(timeout=1)

    def test_handler_skips_duplicates(self, tmp_path):
        """Test that handler skips duplicate files"""
        mock_client = Mock()
        mock_state = Mock()
        mock_state.is_duplicate.return_value = True  # Simulate duplicate

        handler = ScanFileHandler(
            project_id="test",
            api_client=mock_client,
            patterns=["*.xml"],
            exclude_patterns=[],
            delay=0,
            state_manager=mock_state,
            force_reprocess=False
        )

        test_file = tmp_path / "scan.xml"
        test_file.write_text("<nmaprun></nmaprun>")

        # Process file
        handler._process_file(str(test_file))

        # API should not be called for duplicates
        assert not mock_client.import_scan.called

        # Cleanup
        handler.shutdown(timeout=1)

    def test_handler_force_reprocess_overrides_duplicate(self, tmp_path):
        """Test that force_reprocess overrides duplicate detection"""
        mock_client = Mock()
        mock_client.import_scan.return_value = {
            'scan_id': 'test-id',
            'host_count': 1,
            'service_count': 1,
            'status': 'completed'
        }

        mock_state = Mock()
        mock_state.is_duplicate.return_value = True  # Simulate duplicate

        handler = ScanFileHandler(
            project_id="test",
            api_client=mock_client,
            patterns=["*.xml"],
            exclude_patterns=[],
            delay=0,
            state_manager=mock_state,
            force_reprocess=True  # Force reprocessing
        )

        test_file = tmp_path / "scan.xml"
        test_file.write_text("<nmaprun></nmaprun>")

        # Process file
        handler._process_file(str(test_file))

        # API should be called even for duplicates
        assert mock_client.import_scan.called

        # Cleanup
        handler.shutdown(timeout=1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

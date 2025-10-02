import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from services import ScanImportService, ScanImportResult, ImportProgress
from parsers.base import UnsupportedScanError, CorruptedScanError
from models.scan import ScanStatus, ToolType


class TestScanImportService:
    """Test cases for ScanImportService"""

    def setup_method(self):
        self.session = Mock()
        self.service = ScanImportService(self.session)
        self.project_id = uuid4()

        # Mock the repositories
        self.service.scan_repo = Mock()
        self.service.host_repo = Mock()
        self.service.service_repo = Mock()

    def test_service_initialization(self):
        """Test service initializes correctly"""
        assert self.service.session == self.session
        assert self.service.parser_factory is not None
        assert self.service.scan_repo is not None
        assert self.service.host_repo is not None
        assert self.service.service_repo is not None

    def test_set_progress_callback(self):
        """Test setting progress callback"""
        callback = Mock()
        self.service.set_progress_callback(callback)
        assert self.service._progress_callback == callback

    def test_import_scan_success(self):
        """Test successful scan import"""
        # Mock parser factory and parser
        mock_parser = Mock()
        mock_parser.parse.return_value = []  # Empty host list for simplicity
        self.service.parser_factory.get_parser = Mock(return_value=mock_parser)

        # Mock repositories
        mock_scan = Mock()
        mock_scan.id = uuid4()
        self.service.scan_repo.create.return_value = mock_scan
        self.service.scan_repo.update.return_value = mock_scan

        # Test import
        result = self.service.import_scan(
            project_id=self.project_id,
            filename="test.xml",
            content='<?xml version="1.0"?><nmaprun>test</nmaprun>',
            tool_type="nmap"
        )

        # Verify result
        assert isinstance(result, ScanImportResult)
        assert result.success is True
        assert result.scan_id == mock_scan.id
        assert result.processing_time_ms >= 0  # Changed from > 0 since mock may be very fast

        # Verify scan creation and update
        self.service.scan_repo.create.assert_called_once()
        self.service.scan_repo.update.assert_called()

    def test_import_scan_unsupported_format(self):
        """Test import with unsupported file format"""
        # Mock parser factory to raise UnsupportedScanError
        self.service.parser_factory.get_parser = Mock(side_effect=UnsupportedScanError("Unsupported format"))

        # Mock scan creation
        mock_scan = Mock()
        mock_scan.id = uuid4()
        self.service.scan_repo.create.return_value = mock_scan

        # Test import
        result = self.service.import_scan(
            project_id=self.project_id,
            filename="test.txt",
            content="unsupported content",
            tool_type="auto"
        )

        # Verify result
        assert result.success is False
        assert "Unsupported format" in result.error_message
        assert result.scan_id == mock_scan.id

        # Verify scan status was updated to failed
        self.service.scan_repo.update.assert_called_with(
            mock_scan.id,
            status=ScanStatus.FAILED,
            error_details="Unsupported format"
        )

    def test_import_scan_corrupted_file(self):
        """Test import with corrupted file"""
        # Mock parser to raise CorruptedScanError
        mock_parser = Mock()
        mock_parser.parse.side_effect = CorruptedScanError("File is corrupted")
        self.service.parser_factory.get_parser = Mock(return_value=mock_parser)

        # Mock scan creation
        mock_scan = Mock()
        mock_scan.id = uuid4()
        self.service.scan_repo.create.return_value = mock_scan

        # Test import
        result = self.service.import_scan(
            project_id=self.project_id,
            filename="corrupted.xml",
            content="corrupted xml content",
            tool_type="nmap"
        )

        # Verify result
        assert result.success is False
        assert "File is corrupted" in result.error_message

    def test_create_scan_record_auto_detect_nmap(self):
        """Test scan record creation with auto-detection for Nmap"""
        # Mock scan repository
        mock_scan = Mock()
        self.service.scan_repo.create.return_value = mock_scan

        content = '<?xml version="1.0"?><nmaprun scanner="nmap">test</nmaprun>'

        scan = self.service._create_scan_record(
            project_id=self.project_id,
            filename="scan.xml",
            content=content,
            tool_type="auto"
        )

        # Verify scan creation was called with correct parameters
        create_args = self.service.scan_repo.create.call_args[1]
        assert create_args['project_id'] == self.project_id
        assert create_args['filename'] == "scan.xml"
        assert create_args['tool_type'] == ToolType.NMAP
        assert create_args['status'] == ScanStatus.PROCESSING

    def test_create_scan_record_explicit_tool_type(self):
        """Test scan record creation with explicit tool type"""
        # Mock scan repository
        mock_scan = Mock()
        self.service.scan_repo.create.return_value = mock_scan

        scan = self.service._create_scan_record(
            project_id=self.project_id,
            filename="scan.json",
            content="json content",
            tool_type="masscan"
        )

        # Verify tool type mapping
        create_args = self.service.scan_repo.create.call_args[1]
        assert create_args['tool_type'] == ToolType.MASSCAN

    def test_create_scan_record_unknown_tool_type(self):
        """Test scan record creation with unknown tool type"""
        # Mock scan repository
        mock_scan = Mock()
        self.service.scan_repo.create.return_value = mock_scan

        scan = self.service._create_scan_record(
            project_id=self.project_id,
            filename="scan.txt",
            content="unknown content",
            tool_type="unknown"
        )

        # Verify defaults to CUSTOM
        create_args = self.service.scan_repo.create.call_args[1]
        assert create_args['tool_type'] == ToolType.CUSTOM

    def test_update_progress_with_callback(self):
        """Test progress updates with callback"""
        callback = Mock()
        self.service.set_progress_callback(callback)

        progress = ImportProgress(
            total_hosts=10,
            processed_hosts=5,
            current_stage="importing",
            percentage=50.0
        )

        self.service._update_progress(progress)

        # Verify callback was called with progress
        callback.assert_called_once_with(progress)

    def test_update_progress_without_callback(self):
        """Test progress updates without callback (should not crash)"""
        progress = ImportProgress(
            total_hosts=10,
            processed_hosts=5,
            current_stage="importing",
            percentage=50.0
        )

        # Should not raise exception
        self.service._update_progress(progress)

    @patch('services.scan_import.ScanImportService._process_host_batch')
    def test_import_hosts_batch_processing(self, mock_process_batch):
        """Test batch processing of hosts"""
        # Create mock parsed hosts
        from parsers.base import ParsedHost, ParsedService

        parsed_hosts = [
            ParsedHost(ip_address=f"192.168.1.{i}", services=[])
            for i in range(1, 101)  # 100 hosts
        ]

        # Mock batch processing result
        mock_batch_result = ScanImportResult(scan_id=uuid4(), success=True)
        mock_batch_result.hosts_imported = 50
        mock_batch_result.services_imported = 0
        mock_process_batch.return_value = mock_batch_result

        progress = ImportProgress(total_hosts=100)

        result = self.service._import_hosts_batch(
            scan_id=uuid4(),
            project_id=self.project_id,
            parsed_hosts=parsed_hosts,
            progress=progress
        )

        # Verify batching - should be called twice (50 hosts per batch)
        assert mock_process_batch.call_count == 2

        # Verify accumulated results
        assert result.hosts_imported == 100  # 50 * 2 batches

    def test_get_import_statistics(self):
        """Test getting import statistics for a scan"""
        scan_id = uuid4()

        # Mock scan
        mock_scan = Mock()
        mock_scan.filename = "test.xml"
        mock_scan.status = ScanStatus.COMPLETED
        mock_scan.tool_type = ToolType.NMAP
        mock_scan.processing_time_ms = 5000
        mock_scan.parsed_at = datetime.now()
        mock_scan.error_details = None

        self.service.scan_repo.get_by_id.return_value = mock_scan

        # Mock hosts and services
        mock_hosts = [Mock() for _ in range(5)]
        self.service.host_repo.get_by_project_id.return_value = mock_hosts
        self.service.service_repo.get_by_host_id.return_value = [Mock(), Mock()]  # 2 services per host

        stats = self.service.get_import_statistics(scan_id)

        # Verify statistics
        assert stats['filename'] == "test.xml"
        assert stats['status'] == ScanStatus.COMPLETED.value
        assert stats['tool_type'] == ToolType.NMAP.value
        assert stats['processing_time_ms'] == 5000
        assert stats['total_hosts_in_project'] == 5
        assert stats['total_services_in_project'] == 10  # 5 hosts * 2 services

    def test_get_import_statistics_nonexistent_scan(self):
        """Test getting statistics for non-existent scan"""
        scan_id = uuid4()
        self.service.scan_repo.get_by_id.return_value = None

        stats = self.service.get_import_statistics(scan_id)

        # Should return empty dict
        assert stats == {}
        
        # Verify get_by_id was called but not other repo methods
        self.service.scan_repo.get_by_id.assert_called_once_with(scan_id)
        self.service.host_repo.get_by_project_id.assert_not_called()


class TestImportDataStructures:
    """Test the import data structures"""

    def test_import_progress_creation(self):
        """Test ImportProgress creation and defaults"""
        progress = ImportProgress()

        assert progress.total_hosts == 0
        assert progress.processed_hosts == 0
        assert progress.current_stage == "starting"
        assert progress.percentage == 0.0
        assert progress.start_time is None

    def test_import_progress_with_values(self):
        """Test ImportProgress with specified values"""
        start_time = datetime.now()
        progress = ImportProgress(
            total_hosts=100,
            processed_hosts=50,
            current_stage="importing",
            percentage=50.0,
            start_time=start_time
        )

        assert progress.total_hosts == 100
        assert progress.processed_hosts == 50
        assert progress.current_stage == "importing"
        assert progress.percentage == 50.0
        assert progress.start_time == start_time

    def test_scan_import_result_creation(self):
        """Test ScanImportResult creation and defaults"""
        scan_id = uuid4()
        result = ScanImportResult(scan_id=scan_id, success=True)

        assert result.scan_id == scan_id
        assert result.success is True
        assert result.hosts_imported == 0
        assert result.services_imported == 0
        assert result.processing_time_ms == 0
        assert result.error_message is None
        assert result.warnings == []

    def test_scan_import_result_with_values(self):
        """Test ScanImportResult with specified values"""
        scan_id = uuid4()
        warnings = ["Warning 1", "Warning 2"]
        result = ScanImportResult(
            scan_id=scan_id,
            success=True,
            hosts_imported=10,
            services_imported=25,
            processing_time_ms=5000,
            warnings=warnings
        )

        assert result.scan_id == scan_id
        assert result.success is True
        assert result.hosts_imported == 10
        assert result.services_imported == 25
        assert result.processing_time_ms == 5000
        assert result.warnings == warnings
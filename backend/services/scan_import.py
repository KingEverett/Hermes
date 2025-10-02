from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import time
import os
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from parsers import ScanParserFactory, ParsedHost, ParsedService
from parsers.base import ScanParsingError, CorruptedScanError, UnsupportedScanError
from models.scan import Scan, ScanStatus, ToolType
from models.host import Host
from models.service import Service, Protocol
from repositories.scan import ScanRepository
from repositories.host import HostRepository
from repositories.service import ServiceRepository

# Configuration defaults (can be overridden via environment variables)
DEFAULT_BATCH_SIZE = int(os.getenv('SCAN_IMPORT_BATCH_SIZE', '50'))
DEFAULT_MAX_RAW_CONTENT_SIZE = int(os.getenv('SCAN_IMPORT_MAX_RAW_CONTENT_SIZE', '50000'))


@dataclass
class ImportProgress:
    """Progress tracking for scan imports"""
    total_hosts: int = 0
    processed_hosts: int = 0
    total_services: int = 0
    processed_services: int = 0
    current_stage: str = "starting"
    percentage: float = 0.0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


@dataclass
class ScanImportResult:
    """Result of a scan import operation"""
    scan_id: UUID
    success: bool
    hosts_imported: int = 0
    services_imported: int = 0
    hosts_updated: int = 0
    services_updated: int = 0
    processing_time_ms: int = 0
    error_message: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ScanImportService:
    """Service for importing scan files with performance optimization"""

    def __init__(
        self,
        session: Session,
        batch_size: Optional[int] = None,
        max_raw_content_size: Optional[int] = None
    ):
        """
        Initialize the scan import service.
        
        Args:
            session: Database session
            batch_size: Number of hosts to process per batch (default: 50 or SCAN_IMPORT_BATCH_SIZE env var)
            max_raw_content_size: Maximum raw content size to store in bytes (default: 50000 or SCAN_IMPORT_MAX_RAW_CONTENT_SIZE env var)
        """
        self.session = session
        self.parser_factory = ScanParserFactory()
        self.scan_repo = ScanRepository(session)
        self.host_repo = HostRepository(session)
        self.service_repo = ServiceRepository(session)
        self._progress_callback: Optional[Callable[[ImportProgress], None]] = None
        self.batch_size = batch_size or DEFAULT_BATCH_SIZE
        self.max_raw_content_size = max_raw_content_size or DEFAULT_MAX_RAW_CONTENT_SIZE

    def set_progress_callback(self, callback: Callable[[ImportProgress], None]) -> None:
        """Set callback function for progress updates"""
        self._progress_callback = callback

    def import_scan(
        self,
        project_id: UUID,
        filename: str,
        content: str,
        tool_type: Optional[str] = None
    ) -> ScanImportResult:
        """
        Import scan file with performance optimization.

        Args:
            project_id: Project UUID
            filename: Original filename
            content: File content as string
            tool_type: Optional tool type ('auto' to detect, or specific type)

        Returns:
            ScanImportResult with import statistics

        Raises:
            UnsupportedScanError: If file format is not supported
            CorruptedScanError: If file is corrupted
            ScanParsingError: For other parsing errors
        """
        start_time = time.time()
        progress = ImportProgress(start_time=datetime.now())

        try:
            # Create scan record
            scan = self._create_scan_record(project_id, filename, content, tool_type)
            progress.current_stage = "parsing"
            self._update_progress(progress)

            # Parse the scan content
            parser = self.parser_factory.get_parser(content, filename)
            parsed_hosts = parser.parse(content)

            # Update progress with totals
            progress.total_hosts = len(parsed_hosts)
            progress.total_services = sum(len(host.services) for host in parsed_hosts)
            progress.current_stage = "importing"
            self._update_progress(progress)

            # Import hosts and services with batch processing
            result = self._import_hosts_batch(scan.id, project_id, parsed_hosts, progress)

            # Update scan status and processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            self.scan_repo.update(
                scan.id,
                status=ScanStatus.COMPLETED,
                parsed_at=datetime.now(),
                processing_time_ms=processing_time_ms
            )

            result.scan_id = scan.id
            result.processing_time_ms = processing_time_ms
            result.success = True

            # Final progress update
            progress.current_stage = "completed"
            progress.percentage = 100.0
            self._update_progress(progress)

            return result

        except (UnsupportedScanError, CorruptedScanError, ScanParsingError) as e:
            # Update scan status to failed
            if 'scan' in locals():
                self.scan_repo.update(
                    scan.id,
                    status=ScanStatus.FAILED,
                    error_details=str(e)
                )

            processing_time_ms = int((time.time() - start_time) * 1000)
            return ScanImportResult(
                scan_id=scan.id if 'scan' in locals() else None,
                success=False,
                error_message=str(e),
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            # Update scan status to failed
            if 'scan' in locals():
                self.scan_repo.update(
                    scan.id,
                    status=ScanStatus.FAILED,
                    error_details=f"Unexpected error: {str(e)}"
                )

            processing_time_ms = int((time.time() - start_time) * 1000)
            return ScanImportResult(
                scan_id=scan.id if 'scan' in locals() else None,
                success=False,
                error_message=f"Unexpected error during import: {str(e)}",
                processing_time_ms=processing_time_ms
            )

    def _create_scan_record(
        self,
        project_id: UUID,
        filename: str,
        content: str,
        tool_type: Optional[str]
    ) -> Scan:
        """Create initial scan record"""
        # Determine tool type
        if tool_type == "auto" or tool_type is None:
            # Auto-detect based on filename and content
            if filename.endswith('.xml') and '<nmaprun' in content[:1000]:
                detected_tool_type = ToolType.NMAP
            else:
                detected_tool_type = ToolType.CUSTOM
        else:
            # Map string to enum
            tool_type_map = {
                'nmap': ToolType.NMAP,
                'masscan': ToolType.MASSCAN,
                'nuclei': ToolType.NUCLEI,
                'custom': ToolType.CUSTOM
            }
            detected_tool_type = tool_type_map.get(tool_type.lower(), ToolType.CUSTOM)

        # Create scan record
        scan_data = {
            'project_id': project_id,
            'filename': filename,
            'tool_type': detected_tool_type,
            'status': ScanStatus.PROCESSING,
            'raw_content': content[:self.max_raw_content_size] if len(content) > self.max_raw_content_size else content  # Limit storage
        }

        return self.scan_repo.create(**scan_data)

    def _import_hosts_batch(
        self,
        scan_id: UUID,
        project_id: UUID,
        parsed_hosts: List[ParsedHost],
        progress: ImportProgress
    ) -> ScanImportResult:
        """Import hosts using batch processing for performance"""
        result = ScanImportResult(scan_id=scan_id, success=True)

        # Process hosts in batches to manage memory and transaction size
        host_batches = [parsed_hosts[i:i + self.batch_size] for i in range(0, len(parsed_hosts), self.batch_size)]

        for batch_idx, batch in enumerate(host_batches):
            try:
                # Process each batch in a separate transaction
                batch_result = self._process_host_batch(project_id, batch, progress)

                # Accumulate results
                result.hosts_imported += batch_result.hosts_imported
                result.hosts_updated += batch_result.hosts_updated
                result.services_imported += batch_result.services_imported
                result.services_updated += batch_result.services_updated
                result.warnings.extend(batch_result.warnings)

                # Commit batch
                self.session.commit()

                # Update progress
                progress.processed_hosts = min(progress.processed_hosts + len(batch), progress.total_hosts)
                progress.percentage = (progress.processed_hosts / progress.total_hosts) * 100 if progress.total_hosts > 0 else 0
                self._update_progress(progress)

            except Exception as e:
                # Rollback batch and continue with next
                self.session.rollback()
                result.warnings.append(f"Failed to process batch {batch_idx + 1}: {str(e)}")
                continue

        return result

    def _process_host_batch(
        self,
        project_id: UUID,
        parsed_hosts: List[ParsedHost],
        progress: ImportProgress
    ) -> ScanImportResult:
        """Process a batch of hosts"""
        result = ScanImportResult(scan_id=None, success=True)

        for parsed_host in parsed_hosts:
            try:
                # Check if host exists (duplicate detection)
                existing_host = self.host_repo.get_by_ip_address(project_id, parsed_host.ip_address)

                if existing_host:
                    # Update existing host
                    updated_host = self._update_existing_host(existing_host, parsed_host)
                    result.hosts_updated += 1
                else:
                    # Create new host
                    updated_host = self._create_new_host(project_id, parsed_host)
                    result.hosts_imported += 1

                # Process services for this host
                service_result = self._process_host_services(updated_host.id, parsed_host.services)
                result.services_imported += service_result.services_imported
                result.services_updated += service_result.services_updated
                result.warnings.extend(service_result.warnings)

                # Update service progress
                progress.processed_services += len(parsed_host.services)

            except Exception as e:
                result.warnings.append(f"Failed to process host {parsed_host.ip_address}: {str(e)}")
                continue

        return result

    def _update_existing_host(self, existing_host: Host, parsed_host: ParsedHost) -> Host:
        """Update existing host with new information"""
        update_data = {}

        # Update hostname if provided and different
        if parsed_host.hostname and parsed_host.hostname != existing_host.hostname:
            update_data['hostname'] = parsed_host.hostname

        # Update OS information if provided and more recent
        if parsed_host.os_family and parsed_host.os_family != existing_host.os_family:
            update_data['os_family'] = parsed_host.os_family

        if parsed_host.os_details and parsed_host.os_details != existing_host.os_details:
            update_data['os_details'] = parsed_host.os_details

        # Update MAC address if provided
        if parsed_host.mac_address and parsed_host.mac_address != existing_host.mac_address:
            update_data['mac_address'] = parsed_host.mac_address

        # Update status (host model uses string, not enum)
        if parsed_host.status != existing_host.status:
            update_data['status'] = parsed_host.status

        # Update last seen timestamp
        update_data['last_seen'] = datetime.now()

        # Update metadata
        if parsed_host.metadata:
            existing_metadata = existing_host.host_metadata or {}
            existing_metadata.update(parsed_host.metadata)
            update_data['host_metadata'] = existing_metadata

        if update_data:
            return self.host_repo.update(existing_host.id, **update_data)
        else:
            return existing_host

    def _create_new_host(self, project_id: UUID, parsed_host: ParsedHost) -> Host:
        """Create new host from parsed data"""
        host_data = {
            'project_id': project_id,
            'ip_address': parsed_host.ip_address,
            'hostname': parsed_host.hostname,
            'os_family': parsed_host.os_family,
            'os_details': parsed_host.os_details,
            'mac_address': parsed_host.mac_address,
            'status': parsed_host.status,
            'confidence_score': parsed_host.confidence_score,
            'first_seen': datetime.now(),
            'last_seen': datetime.now(),
            'host_metadata': parsed_host.metadata or {}
        }

        return self.host_repo.create(**host_data)

    def _process_host_services(
        self,
        host_id: UUID,
        parsed_services: List[ParsedService]
    ) -> ScanImportResult:
        """Process services for a host"""
        result = ScanImportResult(scan_id=None, success=True)

        for parsed_service in parsed_services:
            try:
                # Check if service exists
                existing_services = self.service_repo.get_by_host_id(host_id)
                existing_service = next(
                    (s for s in existing_services
                     if s.port == parsed_service.port and s.protocol == parsed_service.protocol),
                    None
                )

                if existing_service:
                    # Update existing service
                    self._update_existing_service(existing_service, parsed_service)
                    result.services_updated += 1
                else:
                    # Create new service
                    self._create_new_service(host_id, parsed_service)
                    result.services_imported += 1

            except Exception as e:
                result.warnings.append(
                    f"Failed to process service {parsed_service.port}/{parsed_service.protocol}: {str(e)}"
                )
                continue

        return result

    def _update_existing_service(self, existing_service: Service, parsed_service: ParsedService) -> Service:
        """Update existing service with new information"""
        update_data = {}

        # Update service information if provided and different
        if parsed_service.service_name and parsed_service.service_name != existing_service.service_name:
            update_data['service_name'] = parsed_service.service_name

        if parsed_service.product and parsed_service.product != existing_service.product:
            update_data['product'] = parsed_service.product

        if parsed_service.version and parsed_service.version != existing_service.version:
            update_data['version'] = parsed_service.version

        if parsed_service.banner and parsed_service.banner != existing_service.banner:
            update_data['banner'] = parsed_service.banner

        if parsed_service.cpe and parsed_service.cpe != existing_service.cpe:
            update_data['cpe'] = parsed_service.cpe

        # Update confidence if higher (service model uses float, not enum)
        confidence_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
        existing_confidence = existing_service.confidence or 0.0
        new_confidence = confidence_map.get(parsed_service.confidence, 0.6)

        if new_confidence > existing_confidence:
            update_data['confidence'] = new_confidence

        if update_data:
            return self.service_repo.update(existing_service.id, **update_data)
        else:
            return existing_service

    def _create_new_service(self, host_id: UUID, parsed_service: ParsedService) -> Service:
        """Create new service from parsed data"""
        # Map confidence level to float
        confidence_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}

        service_data = {
            'host_id': host_id,
            'port': parsed_service.port,
            'protocol': Protocol(parsed_service.protocol),
            'service_name': parsed_service.service_name,
            'product': parsed_service.product,
            'version': parsed_service.version,
            'banner': parsed_service.banner,
            'cpe': parsed_service.cpe,
            'confidence': confidence_map.get(parsed_service.confidence, 0.6)
        }

        return self.service_repo.create(**service_data)

    def _update_progress(self, progress: ImportProgress) -> None:
        """Update progress via callback if set"""
        if self._progress_callback:
            self._progress_callback(progress)

    def get_import_statistics(self, scan_id: UUID) -> Dict[str, Any]:
        """Get import statistics for a completed scan"""
        scan = self.scan_repo.get_by_id(scan_id)
        if not scan:
            return {}

        # Get host and service counts for the project
        hosts = self.host_repo.get_by_project_id(scan.project_id, limit=10000)  # Large limit for counting
        total_services = sum(len(self.service_repo.get_by_host_id(host.id)) for host in hosts)

        return {
            'scan_id': str(scan_id),
            'filename': scan.filename,
            'status': scan.status.value,
            'tool_type': scan.tool_type.value,
            'processing_time_ms': scan.processing_time_ms,
            'parsed_at': scan.parsed_at.isoformat() if scan.parsed_at else None,
            'total_hosts_in_project': len(hosts),
            'total_services_in_project': total_services,
            'error_details': scan.error_details
        }
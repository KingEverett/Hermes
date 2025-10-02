"""Optimized documentation generation service for large datasets."""

from datetime import datetime
from typing import Dict, List, Any, Optional, Generator
from pathlib import Path
import logging
import time
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from templates import get_template, validate_markdown_syntax
from models.project import Project
from models.host import Host
from models.service import Service
from models.scan import Scan

logger = logging.getLogger(__name__)


class OptimizedDocumentationService:
    """Optimized service for generating markdown documentation from large project datasets."""

    CHUNK_SIZE = 100  # Process hosts in chunks
    BATCH_SIZE = 500  # Batch size for service queries

    def __init__(self, db_session: Session):
        """Initialize optimized documentation service.

        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.markdown_template = get_template('markdown.j2')

    def generate_markdown_chunked(
        self,
        project_id: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """Generate markdown documentation for large projects using chunked processing.

        Args:
            project_id: Project identifier
            progress_callback: Optional callback for progress updates

        Returns:
            str: Generated markdown content

        Raises:
            ValueError: If project not found
            RuntimeError: If generation fails
        """
        start_time = time.time()

        try:
            # Fetch project metadata efficiently
            project = self._fetch_project_metadata(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Fetch scans
            scans = self._fetch_scans_optimized(project_id)

            # Process hosts in chunks and aggregate data
            hosts_data = []
            stats = self._initialize_statistics()

            total_hosts = self._get_host_count(project_id)
            processed_hosts = 0

            for host_chunk in self._fetch_hosts_chunked(project_id):
                # Process chunk
                chunk_data = self._process_host_chunk(host_chunk, stats)
                hosts_data.extend(chunk_data)

                # Update progress
                processed_hosts += len(host_chunk)
                if progress_callback:
                    progress = (processed_hosts / total_hosts * 100) if total_hosts > 0 else 100
                    progress_callback(progress, processed_hosts, total_hosts)

            # Finalize statistics
            self._finalize_statistics(stats, scans, start_time)

            # Render template with collected data
            markdown_content = self.markdown_template.render(
                project=project,
                hosts=hosts_data,
                scans=scans,
                vulnerabilities=[],
                stats=stats,
                timestamp=datetime.now()
            )

            # Validate generated markdown
            if not validate_markdown_syntax(markdown_content):
                logger.warning(f"Generated markdown has validation warnings for project {project_id}")

            generation_time = time.time() - start_time
            logger.info(f"Generated documentation for {total_hosts} hosts in {generation_time:.2f} seconds")

            return markdown_content

        except Exception as e:
            logger.error(f"Failed to generate optimized markdown for project {project_id}: {str(e)}")
            raise RuntimeError(f"Documentation generation failed: {str(e)}")

    def _fetch_project_metadata(self, project_id: str) -> Optional[Project]:
        """Fetch minimal project metadata.

        Args:
            project_id: Project identifier

        Returns:
            Project object or None
        """
        return self.db_session.query(Project).filter(
            Project.id == project_id
        ).first()

    def _fetch_scans_optimized(self, project_id: str) -> List[Scan]:
        """Fetch scans with minimal columns.

        Args:
            project_id: Project identifier

        Returns:
            List of Scan objects
        """
        return self.db_session.query(Scan).filter(
            Scan.project_id == project_id
        ).all()

    def _get_host_count(self, project_id: str) -> int:
        """Get total host count for progress tracking.

        Args:
            project_id: Project identifier

        Returns:
            Total number of hosts
        """
        return self.db_session.query(func.count(Host.id)).filter(
            Host.project_id == project_id
        ).scalar()

    def _fetch_hosts_chunked(
        self,
        project_id: str
    ) -> Generator[List[Host], None, None]:
        """Fetch hosts in chunks for memory-efficient processing.

        Args:
            project_id: Project identifier

        Yields:
            Chunks of Host objects with services
        """
        offset = 0

        while True:
            # Fetch chunk of hosts with their IDs only
            host_chunk = self.db_session.query(Host).filter(
                Host.project_id == project_id
            ).offset(offset).limit(self.CHUNK_SIZE).all()

            if not host_chunk:
                break

            # Fetch services for this chunk in batch
            host_ids = [host.id for host in host_chunk]
            services = self._fetch_services_batch(host_ids)

            # Attach services to hosts
            service_map = defaultdict(list)
            for service in services:
                service_map[service.host_id].append(service)

            for host in host_chunk:
                host.services = service_map.get(host.id, [])

            yield host_chunk
            offset += self.CHUNK_SIZE

    def _fetch_services_batch(self, host_ids: List[str]) -> List[Service]:
        """Fetch services for multiple hosts in a single query.

        Args:
            host_ids: List of host identifiers

        Returns:
            List of Service objects
        """
        if not host_ids:
            return []

        # Batch query for services
        return self.db_session.query(Service).filter(
            Service.host_id.in_(host_ids)
        ).order_by(Service.host_id, Service.port).all()

    def _process_host_chunk(
        self,
        hosts: List[Host],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process a chunk of hosts and update statistics.

        Args:
            hosts: List of Host objects
            stats: Statistics dictionary to update

        Returns:
            List of processed host data
        """
        processed_hosts = []

        for host in hosts:
            # Process host data
            host_data = {
                'ip_address': host.ip_address,
                'hostname': host.hostname,
                'os_family': host.os_family,
                'os_details': host.os_details,
                'mac_address': host.mac_address,
                'status': host.status,
                'first_seen': host.first_seen,
                'last_seen': host.last_seen,
                'services': host.services
            }
            processed_hosts.append(host_data)

            # Update statistics
            stats['host_count'] += 1
            stats['service_count'] += len(host.services)

            # Update port distribution
            for service in host.services:
                key = (service.port, service.protocol)
                if key not in stats['_port_counts']:
                    stats['_port_counts'][key] = {
                        'port': service.port,
                        'protocol': service.protocol,
                        'count': 0,
                        'services': set()
                    }
                stats['_port_counts'][key]['count'] += 1
                if service.service_name:
                    stats['_port_counts'][key]['services'].add(service.service_name)
                    stats['_service_counts'][service.service_name] = \
                        stats['_service_counts'].get(service.service_name, 0) + 1

                # Count by protocol
                if service.protocol == 'tcp':
                    stats['tcp_count'] += 1
                elif service.protocol == 'udp':
                    stats['udp_count'] += 1

        return processed_hosts

    def _initialize_statistics(self) -> Dict[str, Any]:
        """Initialize statistics dictionary.

        Returns:
            Dict with initialized statistics
        """
        return {
            'host_count': 0,
            'service_count': 0,
            'open_port_count': 0,
            'vulnerability_count': 0,
            'critical_count': 0,
            'port_distribution': [],
            'unique_ports': 0,
            'most_common_service': {'name': 'None', 'count': 0},
            'tcp_count': 0,
            'udp_count': 0,
            'total_processing_time': 0,
            'avg_processing_time': 0,
            # Internal counters
            '_port_counts': {},
            '_service_counts': defaultdict(int)
        }

    def _finalize_statistics(
        self,
        stats: Dict[str, Any],
        scans: List[Scan],
        start_time: float
    ) -> None:
        """Finalize statistics after processing all hosts.

        Args:
            stats: Statistics dictionary to finalize
            scans: List of scan objects
            start_time: Processing start time
        """
        # Calculate port distribution
        port_distribution = []
        for port_info in stats['_port_counts'].values():
            port_info['services'] = list(port_info['services'])
            port_distribution.append(port_info)

        port_distribution.sort(key=lambda x: x['count'], reverse=True)
        stats['port_distribution'] = port_distribution[:20]  # Top 20 ports
        stats['unique_ports'] = len(stats['_port_counts'])
        stats['open_port_count'] = len(stats['_port_counts'])

        # Find most common service
        if stats['_service_counts']:
            most_common = max(stats['_service_counts'].items(), key=lambda x: x[1])
            stats['most_common_service'] = {'name': most_common[0], 'count': most_common[1]}

        # Calculate scan statistics
        total_processing_time = sum(scan.processing_time_ms or 0 for scan in scans)
        stats['total_processing_time'] = total_processing_time
        stats['avg_processing_time'] = total_processing_time // len(scans) if scans else 0

        # Clean up internal counters
        del stats['_port_counts']
        del stats['_service_counts']

        # Add generation time
        stats['generation_time_seconds'] = time.time() - start_time

    def export_to_file_optimized(
        self,
        project_id: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """Export optimized markdown documentation to a file.

        Args:
            project_id: Project identifier
            output_path: Optional output file path
            progress_callback: Optional progress callback

        Returns:
            str: Path to the generated file

        Raises:
            RuntimeError: If export fails
        """
        try:
            # Generate markdown content with optimization
            content = self.generate_markdown_chunked(project_id, progress_callback)

            # Determine output path
            if not output_path:
                project = self._fetch_project_metadata(project_id)
                filename = f"{project.name.replace(' ', '_').lower()}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                output_path = Path('exports') / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            Path(output_path).write_text(content, encoding='utf-8')
            logger.info(f"Optimized documentation exported to {output_path}")

            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to export optimized documentation: {str(e)}")
            raise RuntimeError(f"Export failed: {str(e)}")
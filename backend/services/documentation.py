"""Documentation generation service for creating markdown reports."""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from sqlalchemy.orm import Session, joinedload
from jinja2 import Template

from templates import get_template, validate_markdown_syntax
from models.project import Project
from models.host import Host
from models.service import Service
from models.scan import Scan
from repositories.project import ProjectRepository
from repositories.host import HostRepository
from repositories.service import ServiceRepository
from repositories.scan import ScanRepository
from repositories.documentation_repository import DocumentationSectionRepository
from repositories.attack_chain_repository import AttackChainRepository
from models.documentation import SourceType

logger = logging.getLogger(__name__)


class DocumentationService:
    """Service for generating markdown documentation from project data."""

    def __init__(self, db_session: Session):
        """Initialize documentation service.

        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.project_repo = ProjectRepository(db_session)
        self.host_repo = HostRepository(db_session)
        self.service_repo = ServiceRepository(db_session)
        self.scan_repo = ScanRepository(db_session)
        self.documentation_repo = DocumentationSectionRepository(db_session)
        self.attack_chain_repo = AttackChainRepository(db_session)
        self.markdown_template = get_template('markdown.j2')
        self._entity_cache = {}  # Cache for entity resolution

    def generate_markdown(self, project_id: str, include_graph: bool = False, include_attack_chains: bool = True) -> str:
        """Generate markdown documentation for a project.

        Args:
            project_id: Project identifier
            include_graph: Whether to include network topology graph (default: False)
            include_attack_chains: Whether to include attack chains (default: True)

        Returns:
            str: Generated markdown content

        Raises:
            ValueError: If project not found
            RuntimeError: If generation fails
        """
        from uuid import UUID

        try:
            # Convert to UUID if string
            if isinstance(project_id, str):
                project_id = UUID(project_id)

            # Check host count to decide on strategy
            host_count = self.db_session.query(Host).filter(
                Host.project_id == project_id
            ).count()

            # Use optimized version for large datasets
            if host_count > 100:
                from services.documentation_optimized import OptimizedDocumentationService
                optimized_service = OptimizedDocumentationService(self.db_session)
                return optimized_service.generate_markdown_chunked(project_id)

            # Use regular version for smaller datasets
            # Fetch project data
            project_data = self._fetch_project_data(project_id)

            if not project_data:
                raise ValueError(f"Project {project_id} not found")

            # Calculate statistics
            stats = self._calculate_statistics(project_data)

            # Fetch attack chains if requested
            attack_chains = []
            chain_stats = None
            if include_attack_chains:
                attack_chains = self._fetch_attack_chains(project_id)
                if attack_chains:
                    chain_stats = self._calculate_chain_statistics(attack_chains)

            # Render template
            markdown_content = self.markdown_template.render(
                project=project_data['project'],
                hosts=project_data['hosts'],
                scans=project_data['scans'],
                vulnerabilities=project_data.get('vulnerabilities', []),
                stats=stats,
                timestamp=datetime.now(),
                attack_chains=attack_chains,
                chain_stats=chain_stats,
                resolve_entity=self._resolve_chain_entity
            )

            # Fetch and merge manual documentation sections
            manual_sections = self.documentation_repo.get_by_project(project_id)
            markdown_content = self._merge_documentation(markdown_content, manual_sections)

            # Add network topology graph if requested
            if include_graph:
                markdown_content = self._add_network_topology(project_id, markdown_content, project_data)

            # Validate generated markdown
            if not validate_markdown_syntax(markdown_content):
                logger.warning(f"Generated markdown has validation warnings for project {project_id}")

            return markdown_content

        except Exception as e:
            logger.error(f"Failed to generate markdown for project {project_id}: {str(e)}")
            raise RuntimeError(f"Documentation generation failed: {str(e)}")

    def _fetch_project_data(self, project_id: str) -> Dict[str, Any]:
        """Fetch all project data needed for documentation.

        Args:
            project_id: Project identifier

        Returns:
            Dict containing project, hosts, services, and scans
        """
        # Fetch project
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        # Fetch hosts with services using optimized query
        hosts = (
            self.db_session.query(Host)
            .filter(Host.project_id == project_id)
            .options(joinedload(Host.services))
            .all()
        )

        # Fetch scans
        scans = self.scan_repo.get_by_project_id(project_id)

        # Build the data structure
        project_data = {
            'project': project,
            'hosts': hosts,
            'scans': scans,
            'vulnerabilities': []  # Placeholder for future vulnerability implementation
        }

        return project_data

    def _calculate_statistics(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistics from project data.

        Args:
            project_data: Dictionary containing project data

        Returns:
            Dict containing calculated statistics
        """
        hosts = project_data.get('hosts', [])
        scans = project_data.get('scans', [])
        vulnerabilities = project_data.get('vulnerabilities', [])

        # Calculate host and service counts
        host_count = len(hosts)
        service_count = sum(len(host.services) for host in hosts)

        # Calculate port distribution
        port_distribution = self._calculate_port_distribution(hosts)

        # Calculate service statistics
        service_stats = self._calculate_service_statistics(hosts)

        # Calculate scan statistics
        total_processing_time = sum(
            scan.processing_time_ms or 0
            for scan in scans
        )
        avg_processing_time = (
            total_processing_time // len(scans) if scans else 0
        )

        # Count open ports
        open_port_count = len(set(
            (service.port, service.protocol)
            for host in hosts
            for service in host.services
        ))

        # Vulnerability statistics
        vulnerability_count = len(vulnerabilities)
        critical_count = sum(
            1 for v in vulnerabilities
            if getattr(v, 'severity', None) == 'critical'
        )

        stats = {
            'host_count': host_count,
            'service_count': service_count,
            'open_port_count': open_port_count,
            'vulnerability_count': vulnerability_count,
            'critical_count': critical_count,
            'port_distribution': port_distribution,
            'unique_ports': len(port_distribution),
            'most_common_service': service_stats['most_common'],
            'tcp_count': service_stats['tcp_count'],
            'udp_count': service_stats['udp_count'],
            'total_processing_time': total_processing_time,
            'avg_processing_time': avg_processing_time
        }

        return stats

    def _calculate_port_distribution(self, hosts: List[Host]) -> List[Dict[str, Any]]:
        """Calculate port distribution across all hosts.

        Args:
            hosts: List of Host objects

        Returns:
            List of port distribution data sorted by count
        """
        port_counts = {}

        for host in hosts:
            for service in host.services:
                key = (service.port, service.protocol)
                if key not in port_counts:
                    port_counts[key] = {
                        'port': service.port,
                        'protocol': service.protocol,
                        'count': 0,
                        'services': set()
                    }
                port_counts[key]['count'] += 1
                if service.service_name:
                    port_counts[key]['services'].add(service.service_name)

        # Convert to list and sort by count
        distribution = []
        for port_info in port_counts.values():
            port_info['services'] = list(port_info['services'])
            distribution.append(port_info)

        distribution.sort(key=lambda x: x['count'], reverse=True)
        return distribution

    def _calculate_service_statistics(self, hosts: List[Host]) -> Dict[str, Any]:
        """Calculate service-related statistics.

        Args:
            hosts: List of Host objects

        Returns:
            Dict containing service statistics
        """
        service_counts = {}
        tcp_count = 0
        udp_count = 0

        for host in hosts:
            for service in host.services:
                # Count by service name
                if service.service_name:
                    service_counts[service.service_name] = \
                        service_counts.get(service.service_name, 0) + 1

                # Count by protocol
                if service.protocol == 'tcp':
                    tcp_count += 1
                elif service.protocol == 'udp':
                    udp_count += 1

        # Find most common service
        most_common_service = {'name': 'None', 'count': 0}
        if service_counts:
            most_common = max(service_counts.items(), key=lambda x: x[1])
            most_common_service = {'name': most_common[0], 'count': most_common[1]}

        return {
            'most_common': most_common_service,
            'tcp_count': tcp_count,
            'udp_count': udp_count
        }

    def export_to_file(self, project_id: str, output_path: Optional[str] = None) -> str:
        """Export markdown documentation to a file.

        Args:
            project_id: Project identifier
            output_path: Optional output file path

        Returns:
            str: Path to the generated file

        Raises:
            RuntimeError: If export fails
        """
        try:
            # Generate markdown content
            content = self.generate_markdown(project_id)

            # Determine output path
            if not output_path:
                project = self.project_repo.get_by_id(project_id)
                filename = f"{project.name.replace(' ', '_').lower()}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                output_path = Path('exports') / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            Path(output_path).write_text(content, encoding='utf-8')
            logger.info(f"Documentation exported to {output_path}")

            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to export documentation: {str(e)}")
            raise RuntimeError(f"Export failed: {str(e)}")

    def _merge_documentation(
        self,
        automated_content: str,
        manual_sections: List
    ) -> str:
        """Merge automated and manual content with visual markers.

        Args:
            automated_content: Automated markdown content
            manual_sections: List of DocumentationSection objects

        Returns:
            str: Merged markdown content with visual distinction
        """
        if not manual_sections:
            return automated_content

        # Group manual sections by entity type and ID
        sections_by_entity = {}
        for section in manual_sections:
            entity_key = f"{section.entity_type}_{section.entity_id}"
            if entity_key not in sections_by_entity:
                sections_by_entity[entity_key] = []
            sections_by_entity[entity_key].append(section)

        # Build manual research appendix
        manual_appendix = "\n\n---\n\n# Manual Research Notes\n\n"
        manual_appendix += "_The following sections contain manual research notes added by analysts._\n\n"

        for entity_key, sections in sections_by_entity.items():
            for section in sections:
                # Add visual marker based on source type
                if section.source_type == SourceType.MANUAL:
                    marker = "✏️ MANUAL"
                    border_marker = "<!-- MANUAL RESEARCH -->"
                elif section.source_type == SourceType.MIXED:
                    marker = "🔀 MIXED"
                    border_marker = "<!-- MIXED CONTENT -->"
                else:
                    marker = "🤖 AUTOMATED"
                    border_marker = "<!-- AUTOMATED -->"

                manual_appendix += f"\n{border_marker}\n"
                manual_appendix += f"## {section.entity_type.upper()}: {section.entity_id} ({marker})\n\n"
                manual_appendix += f"_Last updated: {section.updated_at.strftime('%Y-%m-%d %H:%M:%S')}_\n"
                if section.created_by:
                    manual_appendix += f"  \n_Author: {section.created_by}_\n"
                manual_appendix += f"\n{section.content}\n\n"
                manual_appendix += "---\n"

        return automated_content + manual_appendix

    def _add_network_topology(
        self,
        project_id: str,
        markdown_content: str,
        project_data: Dict[str, Any]
    ) -> str:
        """Add network topology graph to documentation.

        Args:
            project_id: Project identifier
            markdown_content: Current markdown content
            project_data: Project data dictionary

        Returns:
            str: Markdown content with embedded graph
        """
        try:
            from services.graph_service import GraphService
            import json

            # Create graphs directory
            project_dir = Path("exports") / project_id / "graphs"
            project_dir.mkdir(parents=True, exist_ok=True)

            # Generate network topology
            graph_service = GraphService(self.db_session)
            topology = graph_service.generate_topology(project_id)

            # Save topology as JSON (SVG generation would happen client-side)
            topology_path = project_dir / "network-topology.json"
            with open(topology_path, 'w') as f:
                json.dump(topology, f, indent=2)

            # Get scan sources for caption
            scans = project_data.get('scans', [])
            scan_sources = [f"{scan.scan_type}" for scan in scans[:5]]  # Limit to 5
            if len(scans) > 5:
                scan_sources.append(f"and {len(scans) - 5} more")

            sources_text = ", ".join(scan_sources) if scan_sources else "No scan data"

            # Create topology section
            topology_section = "\n\n---\n\n"
            topology_section += "## Network Topology\n\n"
            topology_section += f"Network topology generated from {len(scans)} scan(s) on {datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n"
            topology_section += f"**Sources:** {sources_text}\n\n"
            topology_section += f"**Statistics:**\n"
            topology_section += f"- Hosts: {len(project_data.get('hosts', []))}\n"
            topology_section += f"- Services: {sum(len(host.services) for host in project_data.get('hosts', []))}\n"
            topology_section += f"- Vulnerabilities: {len(project_data.get('vulnerabilities', []))}\n\n"

            # Note: SVG would be generated client-side or via separate export
            topology_section += f"_Network topology data available at: `{topology_path.relative_to(Path('exports') / project_id)}`_\n\n"

            # Insert topology section after the executive summary or at the beginning
            if "# Executive Summary" in markdown_content:
                # Insert after executive summary
                parts = markdown_content.split("# Executive Summary", 1)
                if len(parts) == 2:
                    # Find the next section header
                    next_section_pos = parts[1].find("\n# ")
                    if next_section_pos != -1:
                        markdown_content = (
                            parts[0] + "# Executive Summary" +
                            parts[1][:next_section_pos] +
                            topology_section +
                            parts[1][next_section_pos:]
                        )
                    else:
                        markdown_content = parts[0] + "# Executive Summary" + parts[1] + topology_section
            else:
                # Insert at beginning after title
                lines = markdown_content.split('\n', 2)
                if len(lines) >= 2:
                    markdown_content = lines[0] + '\n' + lines[1] + topology_section + '\n' + (lines[2] if len(lines) > 2 else '')

            logger.info(f"Added network topology to documentation for project {project_id}")
            return markdown_content

        except Exception as e:
            logger.error(f"Failed to add network topology: {str(e)}")
            # Return original content if topology generation fails
            return markdown_content

    def _fetch_attack_chains(self, project_id: str) -> List:
        """Fetch all attack chains for a project with nodes eagerly loaded.

        Args:
            project_id: Project identifier

        Returns:
            List of AttackChain objects with nodes loaded
        """
        from uuid import UUID

        try:
            # Convert to UUID if string
            if isinstance(project_id, str):
                project_id = UUID(project_id)

            chains = self.attack_chain_repo.get_project_chains(project_id)
            logger.info(f"Fetched {len(chains)} attack chains for project {project_id}")
            return chains
        except Exception as e:
            logger.error(f"Failed to fetch attack chains: {str(e)}")
            return []

    def _calculate_chain_statistics(self, attack_chains: List) -> Dict[str, Any]:
        """Calculate statistics for attack chains.

        Args:
            attack_chains: List of AttackChain objects

        Returns:
            Dict containing chain statistics
        """
        total_nodes = 0
        total_branches = 0
        total_chains = len(attack_chains)

        for chain in attack_chains:
            total_nodes += len(chain.nodes)
            total_branches += sum(1 for node in chain.nodes if node.is_branch_point)

        return {
            'total_chains': total_chains,
            'total_nodes': total_nodes,
            'total_branches': total_branches,
            'avg_nodes_per_chain': total_nodes // total_chains if total_chains > 0 else 0
        }

    def _resolve_chain_entity(self, entity_type: str, entity_id: str) -> str:
        """Resolve attack chain entity to human-readable string.

        Args:
            entity_type: 'host' or 'service'
            entity_id: UUID of entity

        Returns:
            Formatted string for display
        """
        from uuid import UUID

        # Check cache first
        cache_key = (entity_type, str(entity_id))
        if cache_key in self._entity_cache:
            return self._entity_cache[cache_key]

        result = f"[Entity not found: {entity_id}]"

        try:
            # Convert to UUID if string
            if isinstance(entity_id, str):
                entity_id = UUID(entity_id)

            if entity_type == 'host':
                host = self.host_repo.get_by_id(entity_id)
                if host:
                    hostname = host.hostname or 'Unknown'
                    result = f"{hostname} ({host.ip_address})"
            elif entity_type == 'service':
                service = self.service_repo.get_by_id(entity_id)
                if service:
                    service_name = service.service_name or 'Unknown'
                    # Handle Protocol enum - get value or lowercase string
                    protocol_str = service.protocol.value if hasattr(service.protocol, 'value') else str(service.protocol).lower()
                    result = f"{service_name} ({service.port}/{protocol_str})"
        except Exception as e:
            logger.warning(f"Failed to resolve entity {entity_type}:{entity_id}: {e}")

        # Cache the result
        self._entity_cache[cache_key] = result
        return result

    def export_chain_svg(self, chain_id: str, project_dir: Path) -> Optional[Path]:
        """Generate simple SVG for attack chain.

        Args:
            chain_id: Attack chain identifier
            project_dir: Project directory for exports

        Returns:
            Path to generated SVG or None if failed
        """
        from uuid import UUID

        try:
            # Convert to UUID if string
            if isinstance(chain_id, str):
                chain_id = UUID(chain_id)

            # Fetch chain with nodes
            chain = self.attack_chain_repo.get_chain_by_id(chain_id)
            if not chain:
                logger.warning(f"Chain {chain_id} not found for SVG export")
                return None

            # Create graphs directory
            graphs_dir = project_dir / "graphs"
            graphs_dir.mkdir(parents=True, exist_ok=True)

            # Sort nodes by sequence order
            sorted_nodes = sorted(chain.nodes, key=lambda n: n.sequence_order)

            # Calculate SVG height based on node count
            svg_height = 100 + len(sorted_nodes) * 80

            # Start SVG content
            svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{svg_height}">
  <!-- Attack Chain: {chain.name} -->
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="{chain.color}" />
    </marker>
  </defs>

  <text x="10" y="30" font-size="20" font-weight="bold" fill="{chain.color}">{chain.name}</text>
  <text x="10" y="60" font-size="14" fill="#666">{(chain.description or '')[:80]}</text>
'''

            y_pos = 100
            for i, node in enumerate(sorted_nodes):
                entity_label = self._resolve_chain_entity(node.entity_type, str(node.entity_id))

                # Draw node circle and label
                svg_content += f'''  <circle cx="50" cy="{y_pos}" r="20" fill="{chain.color}" stroke="#000" stroke-width="2"/>
  <text x="50" y="{y_pos + 5}" text-anchor="middle" fill="#fff" font-weight="bold" font-size="14">{i+1}</text>
  <text x="80" y="{y_pos + 5}" font-size="14" fill="#333">{entity_label}</text>
'''

                # Add method notes if present
                if node.method_notes:
                    svg_content += f'''  <text x="80" y="{y_pos + 20}" font-size="12" fill="#666" font-style="italic">Method: {node.method_notes[:60]}</text>
'''

                # Draw arrow to next node
                if i < len(sorted_nodes) - 1:
                    svg_content += f'''  <line x1="50" y1="{y_pos + 20}" x2="50" y2="{y_pos + 60}" stroke="{chain.color}" stroke-width="2" marker-end="url(#arrow)"/>
'''

                y_pos += 80

            svg_content += '</svg>'

            # Write to file
            output_path = graphs_dir / f"attack-chain-{chain.id}.svg"
            output_path.write_text(svg_content, encoding='utf-8')

            logger.info(f"Generated SVG for chain {chain_id} at {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate SVG for chain {chain_id}: {str(e)}")
            return None
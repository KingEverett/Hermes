"""Unit tests for attack chain markdown documentation generation."""

import pytest
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from models.project import Project
from models.host import Host
from models.service import Service, Protocol
from models.attack_chain import AttackChain, AttackChainNode
from services.documentation import DocumentationService
from repositories.attack_chain_repository import AttackChainRepository


@pytest.fixture
def sample_project(test_db):
    """Create a sample project for testing."""
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="Test project for attack chain documentation"
    )
    test_db.add(project)
    test_db.commit()
    return project


@pytest.fixture
def sample_hosts(test_db, sample_project):
    """Create sample hosts for testing."""
    host1 = Host(
        id=uuid4(),
        project_id=sample_project.id,
        ip_address="192.168.1.10",
        hostname="web-server",
        status="up"
    )
    host2 = Host(
        id=uuid4(),
        project_id=sample_project.id,
        ip_address="10.0.0.50",
        hostname="db-server",
        status="up"
    )
    test_db.add_all([host1, host2])
    test_db.commit()
    return [host1, host2]


@pytest.fixture
def sample_services(test_db, sample_hosts):
    """Create sample services for testing."""
    service1 = Service(
        id=uuid4(),
        host_id=sample_hosts[0].id,
        port=80,
        protocol=Protocol.TCP,
        service_name="http"
    )
    service2 = Service(
        id=uuid4(),
        host_id=sample_hosts[0].id,
        port=22,
        protocol=Protocol.TCP,
        service_name="ssh"
    )
    service3 = Service(
        id=uuid4(),
        host_id=sample_hosts[1].id,
        port=3306,
        protocol=Protocol.TCP,
        service_name="mysql"
    )
    test_db.add_all([service1, service2, service3])
    test_db.commit()
    return [service1, service2, service3]


@pytest.fixture
def sample_attack_chain(test_db, sample_project, sample_hosts, sample_services):
    """Create a sample attack chain with nodes."""
    chain = AttackChain(
        id=uuid4(),
        project_id=sample_project.id,
        name="Web to Database",
        description="SQL injection leading to database access",
        color="#FF6B35"
    )
    test_db.add(chain)
    test_db.flush()

    # Create nodes
    nodes = [
        AttackChainNode(
            id=uuid4(),
            attack_chain_id=chain.id,
            entity_type='host',
            entity_id=sample_hosts[0].id,
            sequence_order=1,
            method_notes="Initial access via phishing"
        ),
        AttackChainNode(
            id=uuid4(),
            attack_chain_id=chain.id,
            entity_type='service',
            entity_id=sample_services[0].id,
            sequence_order=2,
            method_notes="SQL injection in login form",
            is_branch_point=True,
            branch_description="Could also exploit file upload vulnerability"
        ),
        AttackChainNode(
            id=uuid4(),
            attack_chain_id=chain.id,
            entity_type='host',
            entity_id=sample_hosts[1].id,
            sequence_order=3,
            method_notes="Credential reuse"
        ),
        AttackChainNode(
            id=uuid4(),
            attack_chain_id=chain.id,
            entity_type='service',
            entity_id=sample_services[2].id,
            sequence_order=4,
            method_notes="Direct database access"
        )
    ]
    test_db.add_all(nodes)
    test_db.commit()
    test_db.refresh(chain)
    return chain


class TestAttackChainDocumentation:
    """Test suite for attack chain documentation generation."""

    def test_fetch_attack_chains(self, test_db, sample_attack_chain):
        """Test fetching attack chains for a project."""
        doc_service = DocumentationService(test_db)
        chains = doc_service._fetch_attack_chains(str(sample_attack_chain.project_id))

        assert len(chains) == 1
        assert chains[0].id == sample_attack_chain.id
        assert chains[0].name == "Web to Database"
        assert len(chains[0].nodes) == 4

    def test_calculate_chain_statistics(self, test_db, sample_attack_chain):
        """Test calculation of chain statistics."""
        doc_service = DocumentationService(test_db)
        chains = [sample_attack_chain]
        stats = doc_service._calculate_chain_statistics(chains)

        assert stats['total_chains'] == 1
        assert stats['total_nodes'] == 4
        assert stats['total_branches'] == 1
        assert stats['avg_nodes_per_chain'] == 4

    def test_resolve_chain_entity_host(self, test_db, sample_hosts):
        """Test entity resolution returns formatted host string."""
        doc_service = DocumentationService(test_db)
        result = doc_service._resolve_chain_entity('host', str(sample_hosts[0].id))

        assert sample_hosts[0].ip_address in result
        assert sample_hosts[0].hostname in result
        assert "web-server" in result
        assert "192.168.1.10" in result

    def test_resolve_chain_entity_service(self, test_db, sample_services):
        """Test entity resolution returns formatted service string."""
        doc_service = DocumentationService(test_db)
        result = doc_service._resolve_chain_entity('service', str(sample_services[0].id))

        assert "http" in result
        assert "80/tcp" in result

    def test_resolve_chain_entity_missing(self, test_db):
        """Test entity resolution handles missing entities gracefully."""
        doc_service = DocumentationService(test_db)
        fake_id = str(uuid4())
        result = doc_service._resolve_chain_entity('host', fake_id)

        assert "Entity not found" in result
        assert fake_id in result

    def test_resolve_chain_entity_caching(self, test_db, sample_hosts):
        """Test entity resolution caches results."""
        doc_service = DocumentationService(test_db)
        host_id = str(sample_hosts[0].id)

        # First call
        result1 = doc_service._resolve_chain_entity('host', host_id)
        assert len(doc_service._entity_cache) == 1

        # Second call should use cache
        result2 = doc_service._resolve_chain_entity('host', host_id)
        assert result1 == result2
        assert len(doc_service._entity_cache) == 1

    def test_markdown_section_renders(self, test_db, sample_project, sample_attack_chain):
        """Test attack chain section appears in markdown output."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        assert "## Attack Chains" in markdown
        assert sample_attack_chain.name in markdown
        assert sample_attack_chain.description in markdown
        assert f"Nodes: {len(sample_attack_chain.nodes)}" in markdown

    def test_markdown_section_with_metadata(self, test_db, sample_project, sample_attack_chain):
        """Test attack chain metadata appears in markdown."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        assert "Total Chains: 1" in markdown
        assert "Total Nodes: 4" in markdown
        assert "Branch Points: 1" in markdown

    def test_markdown_node_sequence_display(self, test_db, sample_project, sample_attack_chain):
        """Test node sequence displays with proper formatting."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        # Should show numbered list
        assert "1. web-server (192.168.1.10)" in markdown
        assert "2. http (80/tcp)" in markdown
        assert "3. db-server (10.0.0.50)" in markdown
        assert "4. mysql (3306/tcp)" in markdown

        # Should show arrows between nodes
        assert "↓" in markdown

    def test_markdown_method_annotations(self, test_db, sample_project, sample_attack_chain):
        """Test method annotations appear indented under nodes."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        assert "**Method**: Initial access via phishing" in markdown
        assert "**Method**: SQL injection in login form" in markdown
        assert "**Method**: Credential reuse" in markdown

    def test_markdown_branch_points(self, test_db, sample_project, sample_attack_chain):
        """Test branch points render with markdown quote callout."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        assert "> **Branch Point**:" in markdown
        assert "Could also exploit file upload vulnerability" in markdown

    def test_markdown_svg_embed_paths(self, test_db, sample_project, sample_attack_chain):
        """Test SVG embed paths are correct relative to project root."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        expected_path = f"./graphs/attack-chain-{sample_attack_chain.id}.svg"
        assert expected_path in markdown
        assert f"![Attack Chain: {sample_attack_chain.name}]" in markdown

    def test_empty_attack_chains_skips_section(self, test_db, sample_project):
        """Test empty attack chains list skips section rendering."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        # Should not include attack chains section if no chains exist
        assert "## Attack Chains" not in markdown

    def test_include_attack_chains_flag_false(self, test_db, sample_project, sample_attack_chain):
        """Test include_attack_chains=False skips section rendering."""
        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=False)

        # Should not include attack chains section when flag is False
        assert "## Attack Chains" not in markdown
        assert sample_attack_chain.name not in markdown

    def test_export_chain_svg(self, test_db, sample_attack_chain, tmp_path):
        """Test SVG export creates valid file."""
        doc_service = DocumentationService(test_db)
        project_dir = tmp_path / "test_project"

        svg_path = doc_service.export_chain_svg(str(sample_attack_chain.id), project_dir)

        assert svg_path is not None
        assert svg_path.exists()
        assert svg_path.suffix == ".svg"

        # Check SVG content
        content = svg_path.read_text()
        assert "<svg" in content
        assert sample_attack_chain.name in content
        assert sample_attack_chain.color in content

    def test_export_chain_svg_with_method_notes(self, test_db, sample_attack_chain, tmp_path):
        """Test SVG export includes method notes."""
        doc_service = DocumentationService(test_db)
        project_dir = tmp_path / "test_project"

        svg_path = doc_service.export_chain_svg(str(sample_attack_chain.id), project_dir)
        content = svg_path.read_text()

        assert "Method: Initial access via phishing" in content
        assert "Method: SQL injection in login form" in content

    def test_export_chain_svg_missing_chain(self, test_db, tmp_path):
        """Test SVG export handles missing chain gracefully."""
        doc_service = DocumentationService(test_db)
        project_dir = tmp_path / "test_project"
        fake_id = str(uuid4())

        svg_path = doc_service.export_chain_svg(fake_id, project_dir)

        assert svg_path is None

    def test_export_chain_svg_creates_directory(self, test_db, sample_attack_chain, tmp_path):
        """Test SVG export creates graphs directory if needed."""
        doc_service = DocumentationService(test_db)
        project_dir = tmp_path / "test_project"

        # Ensure directory doesn't exist
        assert not (project_dir / "graphs").exists()

        svg_path = doc_service.export_chain_svg(str(sample_attack_chain.id), project_dir)

        # Directory should be created
        assert (project_dir / "graphs").exists()
        assert svg_path.parent.name == "graphs"

    def test_multiple_chains_render(self, test_db, sample_project, sample_hosts, sample_services):
        """Test multiple attack chains render correctly."""
        # Create two chains
        chain1 = AttackChain(
            id=uuid4(),
            project_id=sample_project.id,
            name="Chain 1",
            description="First chain",
            color="#FF0000"
        )
        chain2 = AttackChain(
            id=uuid4(),
            project_id=sample_project.id,
            name="Chain 2",
            description="Second chain",
            color="#00FF00"
        )
        test_db.add_all([chain1, chain2])
        test_db.flush()

        # Add nodes to chains
        node1 = AttackChainNode(
            attack_chain_id=chain1.id,
            entity_type='host',
            entity_id=sample_hosts[0].id,
            sequence_order=1
        )
        node2 = AttackChainNode(
            attack_chain_id=chain2.id,
            entity_type='host',
            entity_id=sample_hosts[1].id,
            sequence_order=1
        )
        test_db.add_all([node1, node2])
        test_db.commit()

        doc_service = DocumentationService(test_db)
        markdown = doc_service.generate_markdown(str(sample_project.id), include_attack_chains=True)

        assert "Chain 1" in markdown
        assert "Chain 2" in markdown
        assert "First chain" in markdown
        assert "Second chain" in markdown
        assert "Total Chains: 2" in markdown

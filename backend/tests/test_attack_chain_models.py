import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from models.attack_chain import AttackChain, AttackChainNode
from models.project import Project


def test_attack_chain_creation(test_db):
    """Test creating an attack chain with valid data"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(
        project_id=project.id,
        name="Web to DC",
        description="Initial foothold via SQL injection",
        color="#FF6B35"
    )
    test_db.add(chain)
    test_db.commit()

    assert chain.id is not None
    assert chain.name == "Web to DC"
    assert chain.color == "#FF6B35"
    assert chain.project_id == project.id


def test_attack_chain_default_color(test_db):
    """Test attack chain uses default color when not specified"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    assert chain.color == "#FF6B35"


def test_attack_chain_invalid_color(test_db):
    """Test attack chain validation rejects invalid color format"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    with pytest.raises(ValueError, match="Color must be in hex format"):
        chain = AttackChain(
            project_id=project.id,
            name="Test Chain",
            color="red"  # Invalid format
        )
        test_db.add(chain)
        test_db.commit()


def test_attack_chain_node_creation(test_db):
    """Test creating attack chain nodes"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    node = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="host",
        entity_id=uuid4(),
        sequence_order=1,
        method_notes="SQL injection in login form"
    )
    test_db.add(node)
    test_db.commit()

    assert node.id is not None
    assert node.entity_type == "host"
    assert node.sequence_order == 1
    assert node.is_branch_point is False


def test_attack_chain_node_sequence_uniqueness(test_db):
    """Test that sequence_order must be unique within a chain"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    node1 = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="host",
        entity_id=uuid4(),
        sequence_order=1
    )
    node2 = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="host",
        entity_id=uuid4(),
        sequence_order=1  # Duplicate sequence_order
    )

    test_db.add(node1)
    test_db.add(node2)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_attack_chain_node_invalid_entity_type(test_db):
    """Test that entity_type validation rejects invalid types"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    with pytest.raises(ValueError, match="entity_type must be 'host' or 'service'"):
        node = AttackChainNode(
            attack_chain_id=chain.id,
            entity_type="invalid_type",
            entity_id=uuid4(),
            sequence_order=1
        )
        test_db.add(node)
        test_db.commit()


def test_attack_chain_node_invalid_sequence_order(test_db):
    """Test that sequence_order must be positive"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    with pytest.raises(ValueError, match="sequence_order must be >= 1"):
        node = AttackChainNode(
            attack_chain_id=chain.id,
            entity_type="host",
            entity_id=uuid4(),
            sequence_order=0  # Invalid
        )
        test_db.add(node)
        test_db.commit()


def test_attack_chain_cascade_delete(test_db):
    """Test that deleting a chain cascades to delete nodes"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    node1 = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="host",
        entity_id=uuid4(),
        sequence_order=1
    )
    node2 = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="service",
        entity_id=uuid4(),
        sequence_order=2
    )
    test_db.add_all([node1, node2])
    test_db.commit()

    chain_id = chain.id
    node1_id = node1.id
    node2_id = node2.id

    # Delete the chain
    test_db.delete(chain)
    test_db.commit()

    # Verify nodes were deleted
    assert test_db.query(AttackChainNode).filter_by(id=node1_id).first() is None
    assert test_db.query(AttackChainNode).filter_by(id=node2_id).first() is None
    assert test_db.query(AttackChain).filter_by(id=chain_id).first() is None


def test_attack_chain_branch_point(test_db):
    """Test creating a branch point node"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    node = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="host",
        entity_id=uuid4(),
        sequence_order=1,
        method_notes="SSH credential reuse",
        is_branch_point=True,
        branch_description="Could pivot to mail server with same credentials"
    )
    test_db.add(node)
    test_db.commit()

    assert node.is_branch_point is True
    assert "mail server" in node.branch_description


def test_attack_chain_relationship_to_project(test_db):
    """Test attack chain relationship to project"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    # Refresh to load relationships
    test_db.refresh(project)

    assert len(project.attack_chains) == 1
    assert project.attack_chains[0].name == "Test Chain"


def test_attack_chain_nodes_ordering(test_db):
    """Test that nodes are ordered by sequence_order"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    chain = AttackChain(project_id=project.id, name="Test Chain")
    test_db.add(chain)
    test_db.commit()

    # Add nodes in reverse order
    node3 = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="host",
        entity_id=uuid4(),
        sequence_order=3
    )
    node1 = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="host",
        entity_id=uuid4(),
        sequence_order=1
    )
    node2 = AttackChainNode(
        attack_chain_id=chain.id,
        entity_type="service",
        entity_id=uuid4(),
        sequence_order=2
    )
    test_db.add_all([node3, node1, node2])
    test_db.commit()

    # Refresh to load relationship
    test_db.refresh(chain)

    # Verify nodes are ordered correctly
    assert len(chain.nodes) == 3
    assert chain.nodes[0].sequence_order == 1
    assert chain.nodes[1].sequence_order == 2
    assert chain.nodes[2].sequence_order == 3

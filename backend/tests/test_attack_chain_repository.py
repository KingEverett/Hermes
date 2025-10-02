import pytest
from uuid import uuid4
from repositories.attack_chain_repository import AttackChainRepository
from models.project import Project
from models.attack_chain import AttackChain, AttackChainNode


def test_create_chain_without_nodes(test_db):
    """Test creating an attack chain without nodes"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)
    chain = repo.create_chain(
        project_id=project.id,
        name="Test Chain",
        description="Test description",
        color="#FF6B35"
    )

    assert chain.id is not None
    assert chain.name == "Test Chain"
    assert chain.color == "#FF6B35"
    assert len(chain.nodes) == 0


def test_create_chain_with_nodes(test_db):
    """Test creating an attack chain with nodes"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    host_id = uuid4()
    service_id = uuid4()

    nodes = [
        {
            "entity_type": "host",
            "entity_id": host_id,
            "sequence_order": 1,
            "method_notes": "SQL injection"
        },
        {
            "entity_type": "service",
            "entity_id": service_id,
            "sequence_order": 2,
            "method_notes": "SSH credential reuse",
            "is_branch_point": True,
            "branch_description": "Could pivot to mail server"
        }
    ]

    repo = AttackChainRepository(test_db)
    chain = repo.create_chain(
        project_id=project.id,
        name="Web to DC",
        description="Attack path",
        nodes=nodes
    )

    assert chain.id is not None
    assert len(chain.nodes) == 2
    assert chain.nodes[0].sequence_order == 1
    assert chain.nodes[0].method_notes == "SQL injection"
    assert chain.nodes[1].is_branch_point is True


def test_get_project_chains(test_db):
    """Test retrieving all chains for a project"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)

    # Create multiple chains
    chain1 = repo.create_chain(project_id=project.id, name="Chain 1")
    chain2 = repo.create_chain(project_id=project.id, name="Chain 2")

    chains = repo.get_project_chains(project.id)

    assert len(chains) == 2
    # Both chains should be present
    chain_names = {chain.name for chain in chains}
    assert chain_names == {"Chain 1", "Chain 2"}


def test_get_chain_by_id(test_db):
    """Test retrieving a single chain by ID"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)
    chain = repo.create_chain(
        project_id=project.id,
        name="Test Chain",
        nodes=[
            {
                "entity_type": "host",
                "entity_id": uuid4(),
                "sequence_order": 1
            }
        ]
    )

    retrieved = repo.get_chain_by_id(chain.id)

    assert retrieved is not None
    assert retrieved.id == chain.id
    assert retrieved.name == "Test Chain"
    assert len(retrieved.nodes) == 1


def test_get_chain_by_id_not_found(test_db):
    """Test retrieving a non-existent chain"""
    repo = AttackChainRepository(test_db)
    chain = repo.get_chain_by_id(uuid4())

    assert chain is None


def test_update_chain_attributes(test_db):
    """Test updating chain name, description, color"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)
    chain = repo.create_chain(
        project_id=project.id,
        name="Original Name",
        description="Original description",
        color="#FF6B35"
    )

    updated = repo.update_chain(
        chain_id=chain.id,
        name="Updated Name",
        description="Updated description",
        color="#4ECDC4"
    )

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"
    assert updated.color == "#4ECDC4"


def test_update_chain_replace_nodes(test_db):
    """Test updating chain and replacing nodes"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)

    # Create chain with 2 nodes
    chain = repo.create_chain(
        project_id=project.id,
        name="Test Chain",
        nodes=[
            {"entity_type": "host", "entity_id": uuid4(), "sequence_order": 1},
            {"entity_type": "service", "entity_id": uuid4(), "sequence_order": 2}
        ]
    )

    assert len(chain.nodes) == 2

    # Update with 3 new nodes
    new_nodes = [
        {"entity_type": "host", "entity_id": uuid4(), "sequence_order": 1},
        {"entity_type": "service", "entity_id": uuid4(), "sequence_order": 2},
        {"entity_type": "host", "entity_id": uuid4(), "sequence_order": 3}
    ]

    updated = repo.update_chain(chain_id=chain.id, nodes=new_nodes)

    assert updated is not None
    assert len(updated.nodes) == 3
    assert updated.nodes[2].sequence_order == 3


def test_update_chain_not_found(test_db):
    """Test updating a non-existent chain"""
    repo = AttackChainRepository(test_db)
    updated = repo.update_chain(chain_id=uuid4(), name="New Name")

    assert updated is None


def test_delete_chain(test_db):
    """Test deleting an attack chain"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)
    chain = repo.create_chain(
        project_id=project.id,
        name="Test Chain",
        nodes=[
            {"entity_type": "host", "entity_id": uuid4(), "sequence_order": 1}
        ]
    )

    chain_id = chain.id
    result = repo.delete_chain(chain_id)

    assert result is True
    assert repo.get_chain_by_id(chain_id) is None


def test_delete_chain_not_found(test_db):
    """Test deleting a non-existent chain"""
    repo = AttackChainRepository(test_db)
    result = repo.delete_chain(uuid4())

    assert result is False


def test_chain_exists(test_db):
    """Test checking if a chain exists"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)
    chain = repo.create_chain(project_id=project.id, name="Test Chain")

    assert repo.chain_exists(chain.id) is True
    assert repo.chain_exists(uuid4()) is False


def test_cascade_delete_nodes(test_db):
    """Test that deleting a chain cascades to delete nodes"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)
    chain = repo.create_chain(
        project_id=project.id,
        name="Test Chain",
        nodes=[
            {"entity_type": "host", "entity_id": uuid4(), "sequence_order": 1},
            {"entity_type": "service", "entity_id": uuid4(), "sequence_order": 2}
        ]
    )

    node_ids = [node.id for node in chain.nodes]
    chain_id = chain.id

    repo.delete_chain(chain_id)

    # Verify nodes were deleted
    for node_id in node_ids:
        assert test_db.query(AttackChainNode).filter_by(id=node_id).first() is None


def test_eager_loading_nodes(test_db):
    """Test that nodes are eagerly loaded to avoid N+1 queries"""
    project = Project(name="Test Project")
    test_db.add(project)
    test_db.commit()

    repo = AttackChainRepository(test_db)

    # Create chain with nodes
    chain = repo.create_chain(
        project_id=project.id,
        name="Test Chain",
        nodes=[
            {"entity_type": "host", "entity_id": uuid4(), "sequence_order": 1},
            {"entity_type": "service", "entity_id": uuid4(), "sequence_order": 2}
        ]
    )

    # Close session to ensure we're not relying on session cache
    test_db.expunge_all()

    # Retrieve chain
    retrieved = repo.get_chain_by_id(chain.id)

    # Access nodes without additional queries (would fail if not eagerly loaded)
    assert len(retrieved.nodes) == 2
    assert retrieved.nodes[0].sequence_order == 1

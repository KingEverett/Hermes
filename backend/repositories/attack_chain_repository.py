"""
Attack Chain repository for managing attack chain data access.

This repository provides CRUD operations for attack chains and their nodes
with optimized queries using eager loading.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import SQLAlchemyError
from models.attack_chain import AttackChain, AttackChainNode


class AttackChainRepository:
    """Repository for attack chain data access."""

    def __init__(self, session: Session):
        self.session = session

    def get_project_chains(self, project_id: UUID) -> List[AttackChain]:
        """
        Get all attack chains for a project with nodes eagerly loaded.

        Args:
            project_id: UUID of the project

        Returns:
            List of AttackChain objects with nodes relationship loaded
        """
        return (
            self.session.query(AttackChain)
            .filter(AttackChain.project_id == project_id)
            .options(selectinload(AttackChain.nodes))
            .order_by(AttackChain.created_at.desc())
            .all()
        )

    def get_chain_by_id(self, chain_id: UUID) -> Optional[AttackChain]:
        """
        Get a single attack chain by ID with nodes eagerly loaded.

        Args:
            chain_id: UUID of the attack chain

        Returns:
            AttackChain object with nodes or None if not found
        """
        return (
            self.session.query(AttackChain)
            .filter(AttackChain.id == chain_id)
            .options(selectinload(AttackChain.nodes))
            .first()
        )

    def create_chain(self, project_id: UUID, name: str, description: Optional[str] = None,
                     color: str = "#FF6B35", nodes: Optional[List[dict]] = None) -> AttackChain:
        """
        Create a new attack chain with nodes in a transaction.

        Args:
            project_id: UUID of the project
            name: Name of the attack chain
            description: Optional description
            color: Hex color code (default: #FF6B35)
            nodes: Optional list of node data dictionaries

        Returns:
            Created AttackChain object with nodes

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Create attack chain
            chain = AttackChain(
                project_id=project_id,
                name=name,
                description=description,
                color=color
            )
            self.session.add(chain)
            self.session.flush()  # Flush to get chain.id for nodes

            # Create nodes if provided
            if nodes:
                for node_data in nodes:
                    node = AttackChainNode(
                        attack_chain_id=chain.id,
                        entity_type=node_data['entity_type'],
                        entity_id=node_data['entity_id'],
                        sequence_order=node_data['sequence_order'],
                        method_notes=node_data.get('method_notes'),
                        is_branch_point=node_data.get('is_branch_point', False),
                        branch_description=node_data.get('branch_description')
                    )
                    self.session.add(node)

            self.session.commit()
            self.session.refresh(chain)
            return chain
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def update_chain(self, chain_id: UUID, name: Optional[str] = None,
                     description: Optional[str] = None, color: Optional[str] = None,
                     nodes: Optional[List[dict]] = None) -> Optional[AttackChain]:
        """
        Update an attack chain and optionally replace its nodes.

        Args:
            chain_id: UUID of the attack chain to update
            name: Optional new name
            description: Optional new description
            color: Optional new color
            nodes: Optional list of node data to replace existing nodes

        Returns:
            Updated AttackChain object or None if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            chain = self.get_chain_by_id(chain_id)
            if not chain:
                return None

            # Update chain attributes
            if name is not None:
                chain.name = name
            if description is not None:
                chain.description = description
            if color is not None:
                chain.color = color

            # Replace nodes if provided
            if nodes is not None:
                # Delete existing nodes
                for node in chain.nodes:
                    self.session.delete(node)
                self.session.flush()

                # Create new nodes
                for node_data in nodes:
                    node = AttackChainNode(
                        attack_chain_id=chain.id,
                        entity_type=node_data['entity_type'],
                        entity_id=node_data['entity_id'],
                        sequence_order=node_data['sequence_order'],
                        method_notes=node_data.get('method_notes'),
                        is_branch_point=node_data.get('is_branch_point', False),
                        branch_description=node_data.get('branch_description')
                    )
                    self.session.add(node)

            self.session.commit()
            self.session.refresh(chain)
            return chain
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete_chain(self, chain_id: UUID) -> bool:
        """
        Delete an attack chain (cascade deletes nodes automatically).

        Args:
            chain_id: UUID of the attack chain to delete

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            chain = self.get_chain_by_id(chain_id)
            if not chain:
                return False

            self.session.delete(chain)
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def chain_exists(self, chain_id: UUID) -> bool:
        """
        Check if an attack chain exists.

        Args:
            chain_id: UUID of the attack chain

        Returns:
            True if chain exists, False otherwise
        """
        return (
            self.session.query(AttackChain)
            .filter(AttackChain.id == chain_id)
            .first() is not None
        )

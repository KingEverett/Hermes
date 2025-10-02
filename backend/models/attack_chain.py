from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from .base import BaseModel

class AttackChain(BaseModel):
    """
    Represents a documented exploitation path during penetration testing.

    An attack chain tracks the sequence of compromised hosts and services,
    showing how a tester progressed through the network.
    """
    __tablename__ = "attack_chains"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color = Column(String(7), default="#FF6B35", nullable=False)  # Hex color format

    # Relationships
    nodes = relationship(
        "AttackChainNode",
        back_populates="attack_chain",
        cascade="all, delete-orphan",
        order_by="AttackChainNode.sequence_order"
    )
    project = relationship("Project", back_populates="attack_chains")

    @validates('color')
    def validate_color(self, key, value):
        """Validate hex color format (#RRGGBB)"""
        if not value:
            return "#FF6B35"
        if not (value.startswith('#') and len(value) == 7):
            raise ValueError(f"Color must be in hex format #RRGGBB, got: {value}")
        return value

    def __repr__(self):
        return f"<AttackChain(id={self.id}, name='{self.name}', nodes={len(self.nodes) if self.nodes else 0})>"


class AttackChainNode(BaseModel):
    """
    Represents a single hop in an attack chain.

    Each node tracks the compromised entity (host or service), the order in the chain,
    the method used to compromise it, and whether it represents a branch point.
    """
    __tablename__ = "attack_chain_nodes"

    attack_chain_id = Column(UUID(as_uuid=True), ForeignKey("attack_chains.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # 'host' or 'service'
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    sequence_order = Column(Integer, nullable=False)
    method_notes = Column(Text)
    is_branch_point = Column(Boolean, default=False, nullable=False)
    branch_description = Column(Text)

    # Relationships
    attack_chain = relationship("AttackChain", back_populates="nodes")

    # Constraints
    __table_args__ = (
        UniqueConstraint('attack_chain_id', 'sequence_order', name='uq_chain_sequence'),
        CheckConstraint("entity_type IN ('host', 'service')", name='ck_entity_type'),
        {'extend_existing': True}
    )

    @validates('entity_type')
    def validate_entity_type(self, key, value):
        """Validate entity_type is either 'host' or 'service'"""
        if value not in ('host', 'service'):
            raise ValueError(f"entity_type must be 'host' or 'service', got: {value}")
        return value

    @validates('sequence_order')
    def validate_sequence_order(self, key, value):
        """Validate sequence_order is positive"""
        if value < 1:
            raise ValueError(f"sequence_order must be >= 1, got: {value}")
        return value

    def __repr__(self):
        return f"<AttackChainNode(id={self.id}, chain_id={self.attack_chain_id}, seq={self.sequence_order}, type={self.entity_type})>"

#!/usr/bin/env python3
"""
Database initialization script for CI/CD environments.

This script imports all models and initializes the database tables.
It's designed to work with both PostgreSQL and SQLite.
"""

import os
import sys

# Import all models to register them with SQLAlchemy metadata
from models.project import Project
from models.host import Host
from models.service import Service
from models.scan import Scan
from models.vulnerability import Vulnerability
from models.service_vulnerability import ServiceVulnerability
from models.review_queue import ReviewQueue
from models.default_credential import DefaultCredential
from models.api_configuration import ApiProviderConfig
from models.documentation import DocumentationSection, DocumentationVersion, ResearchTemplate
from models.validation import ValidationQueue, ValidationFeedback
from models.quality_metrics import QualityMetrics
from models.graph import GraphNode, GraphEdge, NetworkTopology
from models.attack_chain import AttackChain, AttackChainNode

from database.connection import init_db, engine
from sqlalchemy import text

def main():
    """Initialize the database with all tables."""
    print("Initializing database...")

    # Check if we can connect to the database
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)

    # Create all tables
    try:
        init_db()
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        sys.exit(1)

    print("Database initialization complete!")

if __name__ == "__main__":
    main()
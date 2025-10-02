#!/usr/bin/env python3
"""
Startup script for the Hermes backend.
Runs database migrations and optionally creates sample data.
"""
import os
import sys
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.init import initialize_database, reset_database
from alembic.config import Config
from alembic import command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run database migrations"""
    logger.info("Running database migrations...")

    # Configure Alembic
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))

    # Run migrations
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed")

def main():
    """Main startup function"""
    logger.info("Starting Hermes backend initialization...")

    # Check if we should reset the database
    reset_db = os.getenv("RESET_DATABASE", "false").lower() == "true"
    create_sample = os.getenv("CREATE_SAMPLE_DATA", "true").lower() == "true"

    if reset_db:
        logger.info("Resetting database...")
        reset_database()

    # Always run migrations
    run_migrations()

    # Create sample data if requested
    if create_sample:
        logger.info("Creating sample data...")
        from database.init import create_sample_data
        create_sample_data()

    logger.info("Backend initialization completed successfully")

if __name__ == "__main__":
    main()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from models.base import BaseModel

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hermes.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database by creating all tables"""
    BaseModel.metadata.create_all(bind=engine)

def get_session():
    """Get a database session"""
    return SessionLocal()
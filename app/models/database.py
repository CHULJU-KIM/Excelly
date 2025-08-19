# app/models/database.py
# Database models for SQLAlchemy

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class DBSession(Base):
    """Database model for chat sessions"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    plan = Column(Text, nullable=True)
    temp_file_content = Column(LargeBinary, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string for metadata
    
    # Relationship
    messages = relationship("DBMessage", back_populates="session", cascade="all, delete-orphan")

class DBMessage(Base):
    """Database model for chat messages"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_used = Column(String(100), nullable=True)  # Which AI model was used
    processing_time = Column(Float, nullable=True)  # Processing time in seconds
    message_type = Column(String(50), default="normal", nullable=False)  # 'normal', 'clarification', 'plan', 'solution'
    metadata_json = Column(Text, nullable=True)  # JSON string for message metadata
    
    # Relationship
    session = relationship("DBSession", back_populates="messages")

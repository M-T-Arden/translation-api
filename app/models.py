from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    translations = relationship("TranslationHistory", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")

class TranslationHistory(Base):
    __tablename__ = "translation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    source_lang = Column(String(10), nullable=False)
    target_lang = Column(String(10), nullable=False)
    provider = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="translations")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )

class UserAPIKey(Base):
    __tablename__ = "user_api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # "deepl", "google", "openai"
    encrypted_api_key = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index('idx_user_provider', 'user_id', 'provider', unique=True),
    )
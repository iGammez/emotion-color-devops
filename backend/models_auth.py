"""
Modelos de base de datos para autenticación y usuarios
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    """Modelo de Usuario con roles y permisos"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")  # admin, user, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Datos personales encriptados
    phone = Column(String, nullable=True)  # Encriptado
    address = Column(String, nullable=True)  # Encriptado
    
    # Relación con paletas
    palettes = relationship("PaletteWithUser", back_populates="owner")

class PaletteWithUser(Base):
    """Modelo de Paleta extendido con relación a usuario"""
    __tablename__ = "palettes_with_users"

    id = Column(Integer, primary_key=True, index=True)
    input_text = Column(String, index=True)
    translated_text = Column(String, nullable=True)
    polarity = Column(String)
    colors = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    analysis_method = Column(String, default="hybrid")
    confidence_score = Column(String, nullable=True)
    sentiment_label = Column(String, nullable=True)
    intensity = Column(String, nullable=True)
    emotion_type = Column(String, nullable=True)
    
    # Relación con usuario
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="palettes")
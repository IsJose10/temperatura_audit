from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(150), nullable=False)
    rol = Column(Enum("administrador", "auditor", name="rol_enum"), default="auditor")
    regional = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

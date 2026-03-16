from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class Sede(Base):
    __tablename__ = "sedes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(20), unique=True, nullable=False)
    regional = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Camara(Base):
    __tablename__ = "camaras"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    tipo = Column(String(50), nullable=True)
    activo = Column(Boolean, default=True)

    sede = relationship("Sede", backref="camaras")

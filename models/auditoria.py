from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Enum, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Auditoria(Base):
    __tablename__ = "auditorias"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_auditoria = Column(String(50), unique=True, nullable=False, index=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    auditor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nombre_auditor = Column(String(150), nullable=True)
    fecha = Column(DateTime, server_default=func.now())
    total_camaras = Column(Integer, default=0)
    camaras_auditadas = Column(Integer, default=0)
    estado = Column(Enum("en_progreso", "completada", name="estado_enum"), default="en_progreso")

    sede = relationship("Sede", backref="auditorias")
    auditor = relationship("Usuario", backref="auditorias")
    detalles = relationship("AuditoriaDetalle", back_populates="auditoria")


class AuditoriaDetalle(Base):
    __tablename__ = "auditoria_detalle"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    auditoria_id = Column(Integer, ForeignKey("auditorias.id"), nullable=False)
    camara_id = Column(Integer, ForeignKey("camaras.id"), nullable=False)
    nombre_producto = Column(String(200), nullable=True)
    temperatura = Column(Numeric(5, 2), nullable=True)
    temperatura_pasillo = Column(Numeric(5, 2), nullable=True)
    observaciones = Column(Text, nullable=True)
    foto_url = Column(String(255), nullable=True)
    nombre_auditor = Column(String(150), nullable=True)
    fecha_registro = Column(Date, nullable=True)
    hora_registro = Column(Time, nullable=True)
    registrado_at = Column(DateTime, server_default=func.now())

    auditoria = relationship("Auditoria", back_populates="detalles")
    camara = relationship("Camara", backref="registros")

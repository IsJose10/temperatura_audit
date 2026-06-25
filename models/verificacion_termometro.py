from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func

# ponytail: simple database models for thermometer calibration verification
class VerificacionTermometro(Base):
    __tablename__ = "verificaciones_termometros"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    equipo = Column(String(100), nullable=True)
    serial_patron = Column(String(100), nullable=True)
    observaciones = Column(Text, nullable=True)
    revisado_por = Column(String(150), nullable=True)
    
    # Checkbox actions
    accion_reajuste = Column(Boolean, default=False)
    accion_mantenimiento = Column(Boolean, default=False)
    accion_reemplazo = Column(Boolean, default=False)
    accion_no_aplica = Column(Boolean, default=False)

    creado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    creado_at = Column(DateTime, server_default=func.now())

    sede = relationship("Sede", backref="verificaciones_termometros")
    creador = relationship("Usuario", backref="verificaciones_termometros")
    detalles = relationship("VerificacionTermometroDetalle", back_populates="verificacion", cascade="all, delete-orphan")


class VerificacionTermometroDetalle(Base):
    __tablename__ = "verificacion_termometro_detalles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    verificacion_id = Column(Integer, ForeignKey("verificaciones_termometros.id"), nullable=False)
    asignado_a = Column(String(150), nullable=True)
    serial_id = Column(String(100), nullable=True)
    marca_modelo = Column(String(150), nullable=True)
    estado_fisico = Column(String(20), nullable=True)  # ponytail: CUMPLE / NO CUMPLE
    valor_objetivo = Column(Numeric(5, 2), nullable=False)  # e.g., -18 or 0
    lectura_verificado = Column(Numeric(5, 2), nullable=True)
    lectura_patron = Column(Numeric(5, 2), nullable=True)
    correccion = Column(Numeric(5, 2), nullable=True)
    emp = Column(String(50), default="±1")
    firma_realiza = Column(String(150), nullable=True)
    aprobado = Column(Boolean, default=False)
    rechazado = Column(Boolean, default=False)

    verificacion = relationship("VerificacionTermometro", back_populates="detalles")

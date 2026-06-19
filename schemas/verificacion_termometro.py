from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

# ponytail: simple schemas for request/response validation
class VerificacionTermometroDetalleCreate(BaseModel):
    asignado_a: Optional[str] = None
    serial_id: Optional[str] = None
    marca_modelo: Optional[str] = None
    valor_objetivo: float
    lectura_verificado: Optional[float] = None
    lectura_patron: Optional[float] = None
    correccion: Optional[float] = None
    emp: Optional[str] = "±1"
    firma_realiza: Optional[str] = None
    aprobado: Optional[bool] = False
    rechazado: Optional[bool] = False

class VerificacionTermometroCreate(BaseModel):
    sede_id: int
    fecha: date
    equipo: Optional[str] = None
    serial_patron: Optional[str] = None
    observaciones: Optional[str] = None
    revisado_por: Optional[str] = None
    accion_reajuste: Optional[bool] = False
    accion_mantenimiento: Optional[bool] = False
    accion_reemplazo: Optional[bool] = False
    accion_no_aplica: Optional[bool] = False
    detalles: List[VerificacionTermometroDetalleCreate]

class VerificacionTermometroDetalleResponse(BaseModel):
    id: int
    verificacion_id: int
    asignado_a: Optional[str] = None
    serial_id: Optional[str] = None
    marca_modelo: Optional[str] = None
    valor_objetivo: float
    lectura_verificado: Optional[float] = None
    lectura_patron: Optional[float] = None
    correccion: Optional[float] = None
    emp: Optional[str] = None
    firma_realiza: Optional[str] = None
    aprobado: Optional[bool] = None
    rechazado: Optional[bool] = None

    class Config:
        from_attributes = True

class VerificacionTermometroResponse(BaseModel):
    id: int
    codigo: str
    sede_id: int
    sede_nombre: Optional[str] = None
    fecha: date
    equipo: Optional[str] = None
    serial_patron: Optional[str] = None
    observaciones: Optional[str] = None
    revisado_por: Optional[str] = None
    accion_reajuste: bool
    accion_mantenimiento: bool
    accion_reemplazo: bool
    accion_no_aplica: bool
    creado_por: int
    creador_nombre: Optional[str] = None
    creado_at: datetime
    detalles: List[VerificacionTermometroDetalleResponse] = []

    class Config:
        from_attributes = True

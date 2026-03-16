from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, time


class AuditoriaCreate(BaseModel):
    sede_id: int


class AuditoriaDetalleCreate(BaseModel):
    camara_id: int
    nombre_producto: Optional[str] = None
    temperatura: Optional[float] = None
    observaciones: Optional[str] = None
    foto_url: Optional[str] = None


class AuditoriaDetalleResponse(BaseModel):
    id: int
    camara_id: int
    camara_nombre: Optional[str] = None
    nombre_producto: Optional[str] = None
    temperatura: Optional[float] = None
    observaciones: Optional[str] = None
    foto_url: Optional[str] = None
    nombre_auditor: Optional[str] = None
    fecha_registro: Optional[date] = None
    hora_registro: Optional[time] = None
    registrado_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditoriaResponse(BaseModel):
    id: int
    id_auditoria: str
    sede_id: int
    sede_nombre: Optional[str] = None
    auditor_id: int
    auditor_nombre: Optional[str] = None
    nombre_auditor: Optional[str] = None
    fecha: Optional[datetime] = None
    total_camaras: int
    camaras_auditadas: int
    estado: str
    detalles: Optional[List[AuditoriaDetalleResponse]] = []

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_auditorias: int
    auditorias_hoy: int
    auditorias_completadas: int
    auditorias_en_progreso: int
    total_sedes: int
    total_camaras: int
    auditorias_por_sede: list
    auditorias_por_mes: list

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.auditoria import Auditoria, AuditoriaDetalle
from models.sede import Sede
from models.camara import Camara
from models.usuario import Usuario
from schemas.auditoria import AuditoriaResponse, AuditoriaDetalleResponse
from routes.auth import get_current_user

router = APIRouter(prefix="/api/historico", tags=["Histórico"])


@router.get("/auditorias", response_model=list[AuditoriaResponse])
def get_historico(
    sede_id: Optional[int] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    query = db.query(Auditoria)

    if current_user.rol != "administrador":
        query = query.filter(Auditoria.auditor_id == current_user.id)

    if sede_id:
        query = query.filter(Auditoria.sede_id == sede_id)
    if estado:
        query = query.filter(Auditoria.estado == estado)
    if fecha_desde:
        query = query.filter(Auditoria.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Auditoria.fecha <= fecha_hasta)

    total = query.count()
    auditorias = query.order_by(Auditoria.fecha.desc()).offset((page - 1) * limit).limit(limit).all()

    result = []
    for a in auditorias:
        sede = db.query(Sede).filter(Sede.id == a.sede_id).first()
        auditor = db.query(Usuario).filter(Usuario.id == a.auditor_id).first()
        detalles = []
        for d in a.detalles:
            camara = db.query(Camara).filter(Camara.id == d.camara_id).first()
            detalles.append(AuditoriaDetalleResponse(
                id=d.id,
                camara_id=d.camara_id,
                camara_nombre=camara.nombre if camara else None,
                nombre_producto=d.nombre_producto,
                temperatura=float(d.temperatura) if d.temperatura else None,
                observaciones=d.observaciones,
                foto_url=d.foto_url,
                nombre_auditor=d.nombre_auditor,
                fecha_registro=d.fecha_registro,
                hora_registro=d.hora_registro,
                registrado_at=d.registrado_at
            ))
        result.append(AuditoriaResponse(
            id=a.id,
            id_auditoria=a.id_auditoria,
            sede_id=a.sede_id,
            sede_nombre=sede.nombre if sede else None,
            auditor_id=a.auditor_id,
            auditor_nombre=auditor.nombre_completo if auditor else None,
            nombre_auditor=a.nombre_auditor,
            fecha=a.fecha,
            total_camaras=a.total_camaras,
            camaras_auditadas=a.camaras_auditadas,
            estado=a.estado,
            detalles=detalles
        ))

    return result


@router.get("/auditorias/{id}", response_model=AuditoriaResponse)
def get_auditoria_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    
    a = db.query(Auditoria).filter(Auditoria.id == id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
        
    sede = db.query(Sede).filter(Sede.id == a.sede_id).first()
    auditor = db.query(Usuario).filter(Usuario.id == a.auditor_id).first()
    
    detalles = []
    for d in a.detalles:
        camara = db.query(Camara).filter(Camara.id == d.camara_id).first()
        detalles.append(AuditoriaDetalleResponse(
            id=d.id,
            camara_id=d.camara_id,
            camara_nombre=camara.nombre if camara else None,
            nombre_producto=d.nombre_producto,
            temperatura=float(d.temperatura) if d.temperatura is not None else None,
            observaciones=d.observaciones,
            foto_url=d.foto_url,
            nombre_auditor=d.nombre_auditor,
            fecha_registro=d.fecha_registro,
            hora_registro=d.hora_registro,
            registrado_at=d.registrado_at
        ))
        
    return AuditoriaResponse(
        id=a.id,
        id_auditoria=a.id_auditoria,
        sede_id=a.sede_id,
        sede_nombre=sede.nombre if sede else None,
        auditor_id=a.auditor_id,
        auditor_nombre=auditor.nombre_completo if auditor else None,
        nombre_auditor=a.nombre_auditor,
        fecha=a.fecha,
        total_camaras=a.total_camaras,
        camaras_auditadas=a.camaras_auditadas,
        estado=a.estado,
        detalles=detalles
    )

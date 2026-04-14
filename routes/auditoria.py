from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import base64
import os
import uuid

# Zona horaria Colombia (UTC-5)
COLOMBIA_TZ = timezone(timedelta(hours=-5))

def now_colombia():
    return datetime.now(COLOMBIA_TZ).replace(tzinfo=None)

from database import get_db
from models.auditoria import Auditoria, AuditoriaDetalle
from models.camara import Camara
from models.sede import Sede
from models.usuario import Usuario
from schemas.auditoria import AuditoriaCreate, AuditoriaDetalleCreate, AuditoriaResponse, AuditoriaDetalleResponse
from schemas.camara import SedeResponse, CamaraResponse
from routes.auth import get_current_user
from config_rangos import verificar_cumplimiento

router = APIRouter(prefix="/api", tags=["Auditorías"])

# Ruta absoluta basada en la ubicación del proyecto (evita errores si el servicio
# corre desde un directorio diferente al del proyecto)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(_BASE_DIR, "static", "uploads")


def generate_audit_id(sede_codigo: str) -> str:
    """Generate audit ID like AU-MED-120326154228"""
    now = now_colombia()
    timestamp = now.strftime("%d%m%y%H%M%S")
    return f"AU-{sede_codigo}-{timestamp}"


@router.get("/sedes", response_model=list[SedeResponse])
def get_sedes(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    query = db.query(Sede).filter(Sede.activo == True)

    # Auditors only see sedes from their regional
    if current_user.rol == "auditor" and current_user.regional:
        query = query.filter(Sede.regional == current_user.regional)

    sedes = query.all()
    return [SedeResponse.model_validate(s) for s in sedes]


@router.get("/sedes/{sede_id}/camaras", response_model=list[CamaraResponse])
def get_camaras_by_sede(sede_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    # Validate auditor has access to this sede's regional
    if current_user.rol == "auditor" and current_user.regional:
        sede = db.query(Sede).filter(Sede.id == sede_id).first()
        if sede and sede.regional != current_user.regional:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta regional")

    camaras = db.query(Camara).filter(Camara.sede_id == sede_id, Camara.activo == True).all()
    return [CamaraResponse.model_validate(c) for c in camaras]


@router.post("/auditorias", response_model=AuditoriaResponse)
def create_auditoria(data: AuditoriaCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    sede = db.query(Sede).filter(Sede.id == data.sede_id).first()
    if not sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    # Validate auditor has access to this regional
    if current_user.rol == "auditor" and current_user.regional:
        if sede.regional != current_user.regional:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta regional")

    # Check if there is already an active audit for this sede
    active_audit = db.query(Auditoria).filter(
        Auditoria.sede_id == data.sede_id,
        Auditoria.estado == "en_progreso"
    ).first()
    if active_audit:
        raise HTTPException(status_code=400, detail="Ya existe una auditoría en progreso para esta sede")


    total_camaras = db.query(Camara).filter(Camara.sede_id == data.sede_id, Camara.activo == True).count()
    id_auditoria = generate_audit_id(sede.codigo)

    auditoria = Auditoria(
        id_auditoria=id_auditoria,
        sede_id=data.sede_id,
        auditor_id=current_user.id,
        nombre_auditor=current_user.nombre_completo,
        total_camaras=total_camaras,
        camaras_auditadas=0,
        estado="en_progreso"
    )
    db.add(auditoria)
    db.commit()
    db.refresh(auditoria)

    return AuditoriaResponse(
        id=auditoria.id,
        id_auditoria=auditoria.id_auditoria,
        sede_id=auditoria.sede_id,
        sede_nombre=sede.nombre,
        auditor_id=auditoria.auditor_id,
        auditor_nombre=current_user.nombre_completo,
        nombre_auditor=auditoria.nombre_auditor,
        fecha=auditoria.fecha,
        total_camaras=auditoria.total_camaras,
        camaras_auditadas=auditoria.camaras_auditadas,
        estado=auditoria.estado,
        detalles=[]
    )


@router.get("/auditorias/activa")
def get_auditoria_activa(sede_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    auditoria = db.query(Auditoria).filter(
        Auditoria.sede_id == sede_id,
        Auditoria.estado == "en_progreso"
    ).order_by(Auditoria.fecha.desc()).first()

    if not auditoria:
        return None

    sede = db.query(Sede).filter(Sede.id == auditoria.sede_id).first()
    detalles = []
    for d in auditoria.detalles:
        camara = db.query(Camara).filter(Camara.id == d.camara_id).first()
        detalles.append(AuditoriaDetalleResponse(
            id=d.id,
            camara_id=d.camara_id,
            camara_nombre=camara.nombre if camara else None,
            nombre_producto=d.nombre_producto,
            temperatura=float(d.temperatura) if d.temperatura else None,
            temperatura_pasillo=float(d.temperatura_pasillo) if d.temperatura_pasillo else None,
            observaciones=d.observaciones,
            foto_url=d.foto_url,
            nombre_auditor=d.nombre_auditor,
            fecha_registro=d.fecha_registro,
            hora_registro=d.hora_registro,
            registrado_at=d.registrado_at
        ))

    return AuditoriaResponse(
        id=auditoria.id,
        id_auditoria=auditoria.id_auditoria,
        sede_id=auditoria.sede_id,
        sede_nombre=sede.nombre if sede else None,
        auditor_id=auditoria.auditor_id,
        auditor_nombre=current_user.nombre_completo,
        nombre_auditor=auditoria.nombre_auditor,
        fecha=auditoria.fecha,
        total_camaras=auditoria.total_camaras,
        camaras_auditadas=auditoria.camaras_auditadas,
        estado=auditoria.estado,
        detalles=detalles
    )


@router.post("/auditorias/upload-foto")
def upload_foto(data: dict, current_user: Usuario = Depends(get_current_user)):
    """Receive a Base64 image and save it to static/uploads/"""
    image_data = data.get("image")
    if not image_data:
        raise HTTPException(status_code=400, detail="No se proporcionó imagen")

    # Remove data URL prefix if present
    if "," in image_data:
        image_data = image_data.split(",")[1]

    # Decode and save
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(base64.b64decode(image_data))

    return {"foto_url": f"/static/uploads/{filename}"}


@router.post("/auditorias/{auditoria_id}/detalle", response_model=AuditoriaDetalleResponse)
def add_detalle(auditoria_id: int, data: AuditoriaDetalleCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    auditoria = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not auditoria:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    camara = db.query(Camara).filter(Camara.id == data.camara_id).first()
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    now = now_colombia()

    # Check if already registered
    existing = db.query(AuditoriaDetalle).filter(
        AuditoriaDetalle.auditoria_id == auditoria_id,
        AuditoriaDetalle.camara_id == data.camara_id
    ).first()

    if existing:
        existing.nombre_producto = data.nombre_producto
        existing.temperatura = data.temperatura
        existing.temperatura_pasillo = data.temperatura_pasillo
        existing.observaciones = data.observaciones
        existing.nombre_auditor = current_user.nombre_completo
        existing.fecha_registro = now.date()
        existing.hora_registro = now.time()
        if data.foto_url:
            existing.foto_url = data.foto_url
        db.commit()
        db.refresh(existing)

        # Compliance check (se usa temperatura_pasillo para comparar con el rango)
        sede = db.query(Sede).filter(Sede.id == auditoria.sede_id).first()
        cumplimiento = {"cumple": None, "rango": "No definido"}
        temp_para_cumplimiento = existing.temperatura_pasillo if existing.temperatura_pasillo is not None else existing.temperatura
        if sede and temp_para_cumplimiento is not None:
            cumplimiento = verificar_cumplimiento(sede.nombre, camara.nombre, float(temp_para_cumplimiento))

        return AuditoriaDetalleResponse(
            id=existing.id,
            camara_id=existing.camara_id,
            camara_nombre=camara.nombre,
            nombre_producto=existing.nombre_producto,
            temperatura=float(existing.temperatura) if existing.temperatura else None,
            temperatura_pasillo=float(existing.temperatura_pasillo) if existing.temperatura_pasillo else None,
            observaciones=existing.observaciones,
            foto_url=existing.foto_url,
            nombre_auditor=existing.nombre_auditor,
            fecha_registro=existing.fecha_registro,
            hora_registro=existing.hora_registro,
            registrado_at=existing.registrado_at,
            cumple_rango=cumplimiento.get("cumple"),
            rango_esperado=cumplimiento.get("rango")
        )

    detalle = AuditoriaDetalle(
        auditoria_id=auditoria_id,
        camara_id=data.camara_id,
        nombre_producto=data.nombre_producto,
        temperatura=data.temperatura,
        temperatura_pasillo=data.temperatura_pasillo,
        observaciones=data.observaciones,
        foto_url=data.foto_url,
        nombre_auditor=current_user.nombre_completo,
        fecha_registro=now.date(),
        hora_registro=now.time()
    )
    db.add(detalle)

    auditoria.camaras_auditadas = db.query(AuditoriaDetalle).filter(
        AuditoriaDetalle.auditoria_id == auditoria_id
    ).count() + 1

    if auditoria.camaras_auditadas >= auditoria.total_camaras:
        auditoria.estado = "completada"

    db.commit()
    db.refresh(detalle)

    # Compliance check (se usa temperatura_pasillo para comparar con el rango)
    sede = db.query(Sede).filter(Sede.id == auditoria.sede_id).first()
    cumplimiento = {"cumple": None, "rango": "No definido"}
    temp_para_cumplimiento = detalle.temperatura_pasillo if detalle.temperatura_pasillo is not None else detalle.temperatura
    if sede and temp_para_cumplimiento is not None:
        cumplimiento = verificar_cumplimiento(sede.nombre, camara.nombre, float(temp_para_cumplimiento))

    return AuditoriaDetalleResponse(
        id=detalle.id,
        camara_id=detalle.camara_id,
        camara_nombre=camara.nombre,
        nombre_producto=detalle.nombre_producto,
        temperatura=float(detalle.temperatura) if detalle.temperatura else None,
        temperatura_pasillo=float(detalle.temperatura_pasillo) if detalle.temperatura_pasillo else None,
        observaciones=detalle.observaciones,
        foto_url=detalle.foto_url,
        nombre_auditor=detalle.nombre_auditor,
        fecha_registro=detalle.fecha_registro,
        hora_registro=detalle.hora_registro,
        registrado_at=detalle.registrado_at,
        cumple_rango=cumplimiento.get("cumple"),
        rango_esperado=cumplimiento.get("rango")
    )


@router.put("/auditorias/{auditoria_id}/completar")
def completar_auditoria(auditoria_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    auditoria = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not auditoria:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    auditoria.estado = "completada"
    db.commit()
    return {"message": "Auditoría completada exitosamente"}

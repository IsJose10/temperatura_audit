"""
routes/auditoria.py
-------------------
CRUD de auditorías y detalles de cámara.
Reglas de negocio:
  - La comparación de cumplimiento usa temperatura_pasillo; fallback a temperatura_producto.
  - Fechas/horas se registran en zona horaria Colombia (UTC-5).
  - Las fotos se guardan en rutas absolutas para compatibilidad con Windows Service.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import base64, os, uuid

from database import get_db
from models.auditoria import Auditoria, AuditoriaDetalle
from models.camara import Camara
from models.sede import Sede
from models.usuario import Usuario
from schemas.auditoria import (AuditoriaCreate, AuditoriaDetalleCreate,
                                AuditoriaResponse, AuditoriaDetalleResponse)
from schemas.camara import SedeResponse, CamaraResponse
from routes.auth import get_current_user
from config_rangos import verificar_cumplimiento

router = APIRouter(prefix="/api", tags=["Auditorías"])

# Zona horaria Colombia UTC-5 (el servidor puede estar en cualquier TZ)
_COL_TZ    = timezone(timedelta(hours=-5))
_BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(_BASE_DIR, "static", "uploads")


# ── Helpers ──────────────────────────────────────────────────────────────────

def now_col() -> datetime:
    """Hora actual en Colombia sin tzinfo (compatible con SQLAlchemy)."""
    return datetime.now(_COL_TZ).replace(tzinfo=None)


def _check_cumplimiento(sede_nombre: str, camara_nombre: str, detalle) -> dict:
    """Evalúa si la temperatura_pasillo (o producto como fallback) cumple el rango."""
    temp = detalle.temperatura_pasillo if detalle.temperatura_pasillo is not None else detalle.temperatura
    if temp is None:
        return {"cumple": None, "rango": "No definido"}
    return verificar_cumplimiento(sede_nombre, camara_nombre, float(temp))


def _build_detalle_response(d, camara, cumpl: dict) -> AuditoriaDetalleResponse:
    """Construye AuditoriaDetalleResponse evitando código repetido en los endpoints."""
    return AuditoriaDetalleResponse(
        id=d.id, camara_id=d.camara_id,
        camara_nombre=camara.nombre if camara else None,
        nombre_producto=d.nombre_producto,
        temperatura=float(d.temperatura) if d.temperatura is not None else None,
        temperatura_pasillo=float(d.temperatura_pasillo) if d.temperatura_pasillo is not None else None,
        observaciones=d.observaciones, foto_url=d.foto_url,
        nombre_auditor=d.nombre_auditor,
        fecha_registro=d.fecha_registro, hora_registro=d.hora_registro,
        registrado_at=d.registrado_at,
        cumple_rango=cumpl.get("cumple"),
        rango_esperado=cumpl.get("rango"),
    )


def _assert_regional(current_user, sede):
    """Lanza 403 si un auditor intenta acceder a una regional distinta a la suya."""
    if current_user.rol == "auditor" and current_user.regional:
        if sede and sede.regional != current_user.regional:
            raise HTTPException(403, "No tienes acceso a esta regional")


# ── Sedes / Cámaras ──────────────────────────────────────────────────────────

@router.get("/sedes", response_model=list[SedeResponse])
def get_sedes(db: Session = Depends(get_db),
              current_user: Usuario = Depends(get_current_user)):
    """Lista sedes activas. Los auditores solo ven las de su regional."""
    q = db.query(Sede).filter(Sede.activo == True)
    if current_user.rol == "auditor" and current_user.regional:
        q = q.filter(Sede.regional == current_user.regional)
    return [SedeResponse.model_validate(s) for s in q.all()]


@router.get("/sedes/{sede_id}/camaras", response_model=list[CamaraResponse])
def get_camaras_by_sede(sede_id: int, db: Session = Depends(get_db),
                        current_user: Usuario = Depends(get_current_user)):
    """Lista cámaras activas de una sede. Valida acceso regional del auditor."""
    sede = db.query(Sede).filter(Sede.id == sede_id).first()
    _assert_regional(current_user, sede)
    camaras = db.query(Camara).filter(Camara.sede_id == sede_id,
                                      Camara.activo == True).all()
    return [CamaraResponse.model_validate(c) for c in camaras]


# ── Auditorías ────────────────────────────────────────────────────────────────

@router.post("/auditorias", response_model=AuditoriaResponse)
def create_auditoria(data: AuditoriaCreate, db: Session = Depends(get_db),
                     current_user: Usuario = Depends(get_current_user)):
    """Crea una auditoría nueva. Falla si ya hay una en progreso para la sede."""
    sede = db.query(Sede).filter(Sede.id == data.sede_id).first()
    if not sede:
        raise HTTPException(404, "Sede no encontrada")
    _assert_regional(current_user, sede)

    if db.query(Auditoria).filter(Auditoria.sede_id == data.sede_id,
                                   Auditoria.estado == "en_progreso").first():
        raise HTTPException(400, "Ya existe una auditoría en progreso para esta sede")

    total = db.query(Camara).filter(Camara.sede_id == data.sede_id,
                                    Camara.activo == True).count()
    audit = Auditoria(
        id_auditoria=f"AU-{sede.codigo}-{now_col().strftime('%d%m%y%H%M%S')}",
        sede_id=data.sede_id, auditor_id=current_user.id,
        nombre_auditor=current_user.nombre_completo,
        total_camaras=total, camaras_auditadas=0, estado="en_progreso",
    )
    db.add(audit); db.commit(); db.refresh(audit)

    return AuditoriaResponse(
        id=audit.id, id_auditoria=audit.id_auditoria, sede_id=audit.sede_id,
        sede_nombre=sede.nombre, auditor_id=audit.auditor_id,
        auditor_nombre=current_user.nombre_completo,
        nombre_auditor=audit.nombre_auditor, fecha=audit.fecha,
        total_camaras=audit.total_camaras,
        camaras_auditadas=audit.camaras_auditadas,
        estado=audit.estado, detalles=[],
    )


@router.get("/auditorias/activa")
def get_auditoria_activa(sede_id: int, db: Session = Depends(get_db),
                         current_user: Usuario = Depends(get_current_user)):
    """Retorna la auditoría en progreso de una sede (o null si no existe)."""
    audit = db.query(Auditoria).filter(
        Auditoria.sede_id == sede_id, Auditoria.estado == "en_progreso"
    ).order_by(Auditoria.fecha.desc()).first()
    if not audit:
        return None

    sede = db.query(Sede).filter(Sede.id == audit.sede_id).first()
    detalles = []
    for d in audit.detalles:
        cam = db.query(Camara).filter(Camara.id == d.camara_id).first()
        detalles.append(AuditoriaDetalleResponse(
            id=d.id, camara_id=d.camara_id,
            camara_nombre=cam.nombre if cam else None,
            nombre_producto=d.nombre_producto,
            temperatura=float(d.temperatura) if d.temperatura is not None else None,
            temperatura_pasillo=float(d.temperatura_pasillo) if d.temperatura_pasillo is not None else None,
            observaciones=d.observaciones, foto_url=d.foto_url,
            nombre_auditor=d.nombre_auditor, fecha_registro=d.fecha_registro,
            hora_registro=d.hora_registro, registrado_at=d.registrado_at,
        ))

    return AuditoriaResponse(
        id=audit.id, id_auditoria=audit.id_auditoria, sede_id=audit.sede_id,
        sede_nombre=sede.nombre if sede else None,
        auditor_id=audit.auditor_id, auditor_nombre=current_user.nombre_completo,
        nombre_auditor=audit.nombre_auditor, fecha=audit.fecha,
        total_camaras=audit.total_camaras, camaras_auditadas=audit.camaras_auditadas,
        estado=audit.estado, detalles=detalles,
    )


@router.post("/auditorias/upload-foto")
def upload_foto(data: dict, current_user: Usuario = Depends(get_current_user)):
    """Recibe imagen Base64, la guarda en static/uploads/ y retorna la URL pública."""
    img = data.get("image", "")
    if not img:
        raise HTTPException(400, "No se proporcionó imagen")
    if "," in img:                          # eliminar prefijo data-URL si existe
        img = img.split(",")[1]
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    fname = f"{uuid.uuid4().hex}.jpg"
    with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
        f.write(base64.b64decode(img))
    return {"foto_url": f"/static/uploads/{fname}"}


@router.post("/auditorias/{auditoria_id}/detalle", response_model=AuditoriaDetalleResponse)
def add_detalle(auditoria_id: int, data: AuditoriaDetalleCreate,
                db: Session = Depends(get_db),
                current_user: Usuario = Depends(get_current_user)):
    """
    Agrega o actualiza el detalle de una cámara en una auditoría activa.
    Si la cámara ya fue registrada, sobreescribe el registro anterior.
    El cumplimiento se evalúa con temperatura_pasillo (fallback a temperatura).
    """
    audit = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not audit:
        raise HTTPException(404, "Auditoría no encontrada")
    cam = db.query(Camara).filter(Camara.id == data.camara_id).first()
    if not cam:
        raise HTTPException(404, "Cámara no encontrada")

    now  = now_col()
    sede = db.query(Sede).filter(Sede.id == audit.sede_id).first()

    # ── Actualizar registro existente de la misma cámara ──
    existing = db.query(AuditoriaDetalle).filter(
        AuditoriaDetalle.auditoria_id == auditoria_id,
        AuditoriaDetalle.camara_id == data.camara_id,
    ).first()
    if existing:
        existing.nombre_producto     = data.nombre_producto
        existing.temperatura         = data.temperatura
        existing.temperatura_pasillo = data.temperatura_pasillo
        existing.observaciones       = data.observaciones
        existing.nombre_auditor      = current_user.nombre_completo
        existing.fecha_registro      = now.date()
        existing.hora_registro       = now.time()
        if data.foto_url:
            existing.foto_url = data.foto_url
        db.commit(); db.refresh(existing)
        return _build_detalle_response(existing, cam,
                                       _check_cumplimiento(sede.nombre, cam.nombre, existing))

    # ── Nuevo detalle ──
    detalle = AuditoriaDetalle(
        auditoria_id=auditoria_id, camara_id=data.camara_id,
        nombre_producto=data.nombre_producto, temperatura=data.temperatura,
        temperatura_pasillo=data.temperatura_pasillo,
        observaciones=data.observaciones, foto_url=data.foto_url,
        nombre_auditor=current_user.nombre_completo,
        fecha_registro=now.date(), hora_registro=now.time(),
    )
    db.add(detalle)
    audit.camaras_auditadas = (
        db.query(AuditoriaDetalle)
        .filter(AuditoriaDetalle.auditoria_id == auditoria_id).count() + 1
    )
    if audit.camaras_auditadas >= audit.total_camaras:
        audit.estado = "completada"
    db.commit(); db.refresh(detalle)
    return _build_detalle_response(detalle, cam,
                                   _check_cumplimiento(sede.nombre, cam.nombre, detalle))


@router.put("/auditorias/{auditoria_id}/completar")
def completar_auditoria(auditoria_id: int, db: Session = Depends(get_db),
                        current_user: Usuario = Depends(get_current_user)):
    """Marca manualmente una auditoría como completada."""
    audit = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not audit:
        raise HTTPException(404, "Auditoría no encontrada")
    audit.estado = "completada"
    db.commit()
    return {"message": "Auditoría completada exitosamente"}

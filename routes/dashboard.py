from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, cast, Date
from datetime import datetime, timedelta

from database import get_db
from models.auditoria import Auditoria, AuditoriaDetalle
from models.sede import Sede
from models.camara import Camara
from models.usuario import Usuario
from routes.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    sede_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    today = datetime.now().date()

    total_auditorias = db.query(Auditoria).count()
    auditorias_hoy = db.query(Auditoria).filter(
        cast(Auditoria.fecha, Date) == today
    ).count()
    auditorias_completadas = db.query(Auditoria).filter(
        Auditoria.estado == "completada"
    ).count()
    auditorias_en_progreso = db.query(Auditoria).filter(
        Auditoria.estado == "en_progreso"
    ).count()
    total_sedes = db.query(Sede).filter(Sede.activo == True).count()
    total_camaras = db.query(Camara).filter(Camara.activo == True).count()

    # Auditorias por sede
    auditorias_por_sede = db.query(
        Sede.nombre,
        func.count(Auditoria.id).label("total")
    ).join(Auditoria, Sede.id == Auditoria.sede_id).group_by(Sede.nombre).all()

    # Auditorias últimos 6 meses
    six_months_ago = datetime.now() - timedelta(days=180)
    mes_col = extract("month", Auditoria.fecha)
    anio_col = extract("year", Auditoria.fecha)
    auditorias_por_mes = db.query(
        mes_col.label("mes"),
        anio_col.label("anio"),
        func.count(Auditoria.id).label("total")
    ).filter(
        Auditoria.fecha >= six_months_ago
    ).group_by(anio_col, mes_col).order_by(anio_col, mes_col).all()

    meses_nombres = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    rango_query = db.query(
        Camara.nombre.label("camara"),
        func.min(AuditoriaDetalle.temperatura).label("temp_min"),
        func.max(AuditoriaDetalle.temperatura).label("temp_max")
    ).join(AuditoriaDetalle, Camara.id == AuditoriaDetalle.camara_id)\
     .filter(AuditoriaDetalle.temperatura.isnot(None))

    if sede_id:
        rango_query = rango_query.filter(Camara.sede_id == sede_id)

    rango_camaras = rango_query.group_by(Camara.nombre).all()
     
    # Temperatura promedio por mes
    temp_promedio_por_mes = db.query(
        mes_col.label("mes"),
        anio_col.label("anio"),
        func.avg(AuditoriaDetalle.temperatura).label("promedio")
    ).join(AuditoriaDetalle, Auditoria.id == AuditoriaDetalle.auditoria_id)\
     .filter(Auditoria.fecha >= six_months_ago)\
     .filter(AuditoriaDetalle.temperatura.isnot(None))\
     .group_by(anio_col, mes_col).order_by(anio_col, mes_col).all()

    return {
        "total_auditorias": total_auditorias,
        "auditorias_hoy": auditorias_hoy,
        "auditorias_completadas": auditorias_completadas,
        "auditorias_en_progreso": auditorias_en_progreso,
        "total_sedes": total_sedes,
        "total_camaras": total_camaras,
        "auditorias_por_sede": [
            {"sede": nombre, "total": total} for nombre, total in auditorias_por_sede
        ],
        "auditorias_por_mes": [
            {"mes": meses_nombres[int(mes)], "anio": int(anio), "total": total}
            for mes, anio, total in auditorias_por_mes
        ],
        "rango_camaras": [
            {
                "camara": col.camara, 
                "min": float(col.temp_min) if col.temp_min is not None else None, 
                "max": float(col.temp_max) if col.temp_max is not None else None
            }
            for col in rango_camaras
        ],
        "temperatura_promedio_por_mes": [
            {
                "mes": meses_nombres[int(mes)], 
                "anio": int(anio), 
                "promedio": float(promedio) if promedio is not None else None
            }
            for mes, anio, promedio in temp_promedio_por_mes
        ]
    }

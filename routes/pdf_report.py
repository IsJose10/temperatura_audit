"""
routes/pdf_report.py
---------------------
Generación del reporte PDF FR-CAL-032 (Control de Temperaturas Cámaras).
Regla de cumplimiento: se evalúa temperatura_pasillo; fallback a temperatura_producto.
"""
import io, os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from database import get_db
from models.auditoria import Auditoria, AuditoriaDetalle
from models.camara import Camara
from models.sede import Sede
from models.usuario import Usuario
from routes.auth import get_current_user
from config_rangos import verificar_cumplimiento

router = APIRouter(prefix="/api", tags=["PDF Reports"])

# Zona horaria Colombia UTC-5
_COL_TZ   = timezone(timedelta(hours=-5))
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(_BASE_DIR, "static", "img", "ransa_logo_wide.png")

# Colores corporativos RANSA
_GREEN  = colors.HexColor('#009B3A')
_DARK   = colors.HexColor('#064e3b')
_GRAY   = colors.HexColor('#cccccc')
_STRIPE = colors.HexColor('#f8faf8')

def now_col():
    return datetime.now(_COL_TZ).replace(tzinfo=None)

def _style(name, **kw):
    """Crea un ParagraphStyle rápido a partir del estilo Normal."""
    base = getSampleStyleSheet()['Normal']
    return ParagraphStyle(name, parent=base, **kw)

def _temp_pasillo_o_producto(detalle):
    """Retorna la temperatura que se usa para verificar cumplimiento."""
    if detalle.temperatura_pasillo is not None:
        return float(detalle.temperatura_pasillo)
    return float(detalle.temperatura) if detalle.temperatura is not None else 0.0


# ── Secciones del PDF ─────────────────────────────────────────────────────────

def _header_table():
    """Cabecera FR-CAL-032 con logo RANSA, título y versión."""
    title_s   = _style('T', fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=14)
    sub_s     = _style('S', fontSize=9,  fontName='Helvetica-Bold', alignment=TA_CENTER)
    ver_s     = _style('V', fontSize=8,  fontName='Helvetica',      alignment=TA_CENTER)

    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=1.8*inch, height=0.5*inch)
        logo.hAlign = 'LEFT'
    else:
        logo = Paragraph('<font color="#F7941D"><b>R</b></font>'
                         '<font color="#009B3A"><b>RANSA</b></font>',
                         _style('L', fontSize=18, fontName='Helvetica-Bold',
                                textColor=_GREEN, alignment=TA_LEFT))

    title = Paragraph('CONTROL DE TEMPERATURAS<br/>CÁMARAS DE ALMACENAMIENTO', title_s)
    data  = [[logo, title, Paragraph('Versión: 7', ver_s)],
             ['',   Paragraph('FR-CAL-032', sub_s), '']]
    t = Table(data, colWidths=[2*inch, 5.5*inch, 2*inch])
    t.setStyle(TableStyle([
        ('SPAN',        (0, 0), (0, 1)),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',       (0, 0), (0, -1), 'LEFT'),
        ('ALIGN',       (1, 0), (2, -1), 'CENTER'),
        ('BOX',         (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID',   (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING',  (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def _responsible_table(responsables: str, sede_nombre: str, fecha):
    """Fila de responsables, sede y fecha."""
    s   = _style('I', fontSize=8, fontName='Helvetica')
    dia, mes, anio = fecha.strftime('%d'), fecha.strftime('%m'), fecha.strftime('%Y')
    row = [[
        Paragraph(f'<b>Responsables:</b> {responsables}', s),
        Paragraph(f'<b>Sede:</b> {sede_nombre}', s),
        Paragraph(f'<b>Día</b> {dia}  <b>mes</b> {mes}  <b>año</b> {anio}', s),
    ]]
    t = Table(row, colWidths=[3.3*inch, 3.2*inch, 3*inch])
    t.setStyle(TableStyle([
        ('BOX',         (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID',   (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def _main_data_table(detalles_with_cameras, sede):
    """Tabla principal con los datos de cada cámara auditada."""
    cell_s   = _style('C',  fontSize=7, fontName='Helvetica',      leading=9)
    header_s = _style('CH', fontSize=7, fontName='Helvetica-Bold',
                      alignment=TA_CENTER, leading=9, textColor=colors.white)

    cols    = ['Cámara', 'Rango\nEsperado', 'Temp\nProducto °C', 'Temp\nPasillo °C',
               'Hora', 'Producto', 'Observaciones']
    data    = [[Paragraph(h.replace('\n', '<br/>'), header_s) for h in cols]]

    for d, cam in detalles_with_cameras:
        rangoinfo = verificar_cumplimiento(
            sede.nombre, cam.nombre if cam else "", _temp_pasillo_o_producto(d))
        cname = cam.nombre if cam else f'Cámara {d.camara_id}'
        data.append([
            Paragraph(cname, cell_s),
            Paragraph(rangoinfo["rango"], cell_s),
            Paragraph(f'{float(d.temperatura):.1f}°C'        if d.temperatura        is not None else '', cell_s),
            Paragraph(f'{float(d.temperatura_pasillo):.1f}°C' if d.temperatura_pasillo is not None else '', cell_s),
            Paragraph(d.hora_registro.strftime('%H:%M')       if d.hora_registro      else '',             cell_s),
            Paragraph(d.nombre_producto or '', cell_s),
            Paragraph(d.observaciones   or '', cell_s),
        ])

    # Rellena hasta 9 filas para aspecto consistente
    while len(data) < 10:
        data.append([''] * 7)

    widths = [1.4, 0.8, 0.7, 0.7, 0.5, 1.1, 3.3]
    t = Table(data, colWidths=[w*inch for w in widths], repeatRows=1)
    cmds = [
        ('BACKGROUND',  (0, 0), (-1,  0), _DARK),
        ('TEXTCOLOR',   (0, 0), (-1,  0), colors.white),
        ('FONTNAME',    (0, 0), (-1,  0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1,  0), 7),
        ('ALIGN',       (0, 0), (-1,  0), 'CENTER'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX',         (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID',   (0, 0), (-1, -1), 0.5, _GRAY),
        ('TOPPADDING',  (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',(0, 0), (-1, -1), 4),
    ]
    # Filas alternas con fondo suave
    for i in range(1, len(data), 2):
        cmds.append(('BACKGROUND', (0, i), (-1, i), _STRIPE))
    t.setStyle(TableStyle(cmds))
    return t


def _obs_table(detalles_with_cameras):
    """Sección de observaciones consolidadas."""
    obs_s  = _style('O',  fontSize=8, fontName='Helvetica',      leading=10)
    bold_s = _style('OB', fontSize=8, fontName='Helvetica-Bold', leading=10)
    items  = [f'<b>{cam.nombre if cam else f"Cámara {d.camara_id}"}:</b> {d.observaciones}'
              for d, cam in detalles_with_cameras if d.observaciones]
    texto  = '<br/>'.join(items) if items else 'Sin observaciones.'
    t = Table([[Paragraph('<b>Observaciones:</b>', bold_s)],
               [Paragraph(texto, obs_s)]], colWidths=[9.5*inch])
    t.setStyle(TableStyle([
        ('BOX',         (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID',   (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _sign_table(responsables: str):
    """Sección de firmas con nombres de auditores."""
    sign_s = _style('SG', fontSize=8, fontName='Helvetica-Bold')
    name_s = _style('SN', fontSize=8, fontName='Helvetica', alignment=TA_CENTER)
    line   = '_' * 40
    t = Table([
        [Paragraph(f'<b>Realizado por:</b> {line}', sign_s),
         Paragraph(f'<b>Revisado por:</b> {line}', sign_s)],
        [Paragraph(responsables, name_s), Paragraph('', name_s)],
    ], colWidths=[4.75*inch, 4.75*inch])
    t.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING',  (0, 0), (-1, 0), 8),
        ('TOPPADDING',  (0, 1), (-1, 1), 2),
        ('ALIGN',       (0, 1), (-1, 1), 'CENTER'),
    ]))
    return t


# ── Generador principal ───────────────────────────────────────────────────────

def _generate_pdf(auditoria, sede, detalles_with_cameras, _db) -> io.BytesIO:
    """Ensambla el PDF FR-CAL-032 y retorna un BytesIO listo para streaming."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter),
                            leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.4*inch,  bottomMargin=0.5*inch)

    # Recopila todos los auditores únicos (iniciador + contribuyentes)
    auditors = {auditoria.nombre_auditor} if auditoria.nombre_auditor else set()
    auditors.update(d.nombre_auditor for d, _ in detalles_with_cameras if d.nombre_auditor)
    responsables = " / ".join(auditors)

    fecha = auditoria.fecha or now_col()

    doc.build([
        _header_table(),
        Spacer(1, 8),
        _responsible_table(responsables, sede.nombre, fecha),
        Spacer(1, 6),
        _main_data_table(detalles_with_cameras, sede),
        Spacer(1, 10),
        _obs_table(detalles_with_cameras),
        Spacer(1, 14),
        _sign_table(responsables),
    ])
    buf.seek(0)
    return buf


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/auditorias/{auditoria_id}/pdf")
def download_pdf(auditoria_id: int, db: Session = Depends(get_db),
                 current_user: Usuario = Depends(get_current_user)):
    """Genera y descarga el PDF FR-CAL-032 de una auditoría."""
    audit = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not audit:
        raise HTTPException(404, "Auditoría no encontrada")
    sede = db.query(Sede).filter(Sede.id == audit.sede_id).first()
    if not sede:
        raise HTTPException(404, "Sede no encontrada")

    detalles = db.query(AuditoriaDetalle).filter(
        AuditoriaDetalle.auditoria_id == audit.id).all()
    pairs = [(d, db.query(Camara).filter(Camara.id == d.camara_id).first())
             for d in detalles]

    buf      = _generate_pdf(audit, sede, pairs, db)
    filename = f"FR-CAL-032_{sede.nombre}_{audit.id_auditoria}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/auditorias/{auditoria_id}/cumplimiento")
def get_cumplimiento(auditoria_id: int, db: Session = Depends(get_db),
                     current_user: Usuario = Depends(get_current_user)):
    """
    Retorna el estado de cumplimiento de todas las cámaras de una auditoría.
    Usa temperatura_pasillo para la comparación; fallback a temperatura_producto.
    """
    audit = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not audit:
        raise HTTPException(404, "Auditoría no encontrada")
    sede = db.query(Sede).filter(Sede.id == audit.sede_id).first()
    if not sede:
        raise HTTPException(404, "Sede no encontrada")

    detalles = db.query(AuditoriaDetalle).filter(
        AuditoriaDetalle.auditoria_id == audit.id).all()

    results, cumple_n, nocumple_n = [], 0, 0
    for d in detalles:
        cam   = db.query(Camara).filter(Camara.id == d.camara_id).first()
        cname = cam.nombre if cam else f"Cámara {d.camara_id}"
        temp  = _temp_pasillo_o_producto(d) if (d.temperatura_pasillo or d.temperatura) else None
        check = (verificar_cumplimiento(sede.nombre, cname, temp) if temp is not None
                 else {"cumple": None, "rango": "No definido", "mensaje": "Sin temperatura"})

        if check["cumple"] is True:   cumple_n   += 1
        elif check["cumple"] is False: nocumple_n += 1

        results.append({
            "camara_id": d.camara_id, "camara_nombre": cname,
            "temperatura": float(d.temperatura) if d.temperatura is not None else None,
            **check,
        })

    return {
        "auditoria_id": audit.id, "sede_nombre": sede.nombre,
        "total_camaras": len(detalles),
        "en_cumplimiento": cumple_n, "fuera_de_rango": nocumple_n,
        "detalles": results,
    }

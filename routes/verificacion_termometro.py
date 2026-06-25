import io
import os
from datetime import datetime, date, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from database import get_db
from models.verificacion_termometro import VerificacionTermometro, VerificacionTermometroDetalle
from models.sede import Sede
from models.usuario import Usuario
from schemas.verificacion_termometro import VerificacionTermometroCreate, VerificacionTermometroResponse
from routes.auth import get_current_user

router = APIRouter(prefix="/api/verificaciones", tags=["Verificación de Termómetros"])

# Zona horaria Colombia UTC-5
_COL_TZ = timezone(timedelta(hours=-5))
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(_BASE_DIR, "static", "img", "ransa_logo_wide.png")

# Colores corporativos y de diseño
_GREEN = colors.HexColor('#009B3A')
_ORANGE = colors.HexColor('#F7941D')
_HEADER_ORANGE = colors.HexColor('#f2a900')
_GRAY = colors.HexColor('#cccccc')
_STRIPE = colors.HexColor('#fcfdfc')

def now_col():
    return datetime.now(_COL_TZ)

def format_reading(val: Optional[float]) -> str:
    """Format readings with 1 decimal place using dot separator."""
    if val is None:
        return ""
    return f"{float(val):.1f}"

def format_correction(val: Optional[float]) -> str:
    """Format correction with 2 decimal places using dot separator."""
    if val is None:
        return ""
    return f"{float(val):.2f}"

def _sanitize_filename(name: str) -> str:
    import unicodedata
    normalized = unicodedata.normalize('NFKD', name)
    return "".join(c for c in normalized if not unicodedata.combining(c))

def _style(name, **kw):
    base = getSampleStyleSheet()['Normal']
    return ParagraphStyle(name, parent=base, **kw)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=VerificacionTermometroResponse)
def create_verificacion(
    data: VerificacionTermometroCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    sede = db.query(Sede).filter(Sede.id == data.sede_id).first()
    if not sede:
        raise HTTPException(404, "Sede no encontrada")

    # Generar código único: VT-FON-YYMMDD-XXXX
    date_str = data.fecha.strftime('%y%m%d')
    prefix = f"VT-{sede.codigo}-{date_str}"
    count = db.query(VerificacionTermometro).filter(
        VerificacionTermometro.codigo.like(f"{prefix}%")
    ).count()
    codigo = f"{prefix}-{count + 1:03d}"

    # Crear cabecera
    verif = VerificacionTermometro(
        codigo=codigo,
        sede_id=data.sede_id,
        fecha=data.fecha,
        equipo=data.equipo,
        serial_patron=data.serial_patron,
        observaciones=data.observaciones,
        revisado_por=data.revisado_por,
        accion_reajuste=data.accion_reajuste,
        accion_mantenimiento=data.accion_mantenimiento,
        accion_reemplazo=data.accion_reemplazo,
        accion_no_aplica=data.accion_no_aplica,
        creado_por=current_user.id
    )
    db.add(verif)
    db.flush()

    # Crear detalles
    for det_data in data.detalles:
        corr = None
        if det_data.lectura_verificado is not None and det_data.lectura_patron is not None:
            # Corrección = Lectura Verificado - Lectura Patrón
            corr = float(det_data.lectura_verificado) - float(det_data.lectura_patron)
            corr = round(corr, 2)

        # Autocalcular aprobado/rechazado
        aprobado = det_data.aprobado
        rechazado = det_data.rechazado
        if corr is not None:
            deviation_ok = abs(corr) <= 1.0
            aprobado = deviation_ok
            rechazado = not deviation_ok

        det = VerificacionTermometroDetalle(
            verificacion_id=verif.id,
            asignado_a=det_data.asignado_a,
            serial_id=det_data.serial_id,
            marca_modelo=det_data.marca_modelo,
            estado_fisico=det_data.estado_fisico,
            valor_objetivo=det_data.valor_objetivo,
            lectura_verificado=det_data.lectura_verificado,
            lectura_patron=det_data.lectura_patron,
            correccion=corr,
            emp=det_data.emp or "±1",
            firma_realiza=det_data.firma_realiza,
            aprobado=aprobado,
            rechazado=rechazado
        )
        db.add(det)

    db.commit()
    db.refresh(verif)

    return _build_response_obj(verif, sede, current_user)

@router.get("/historico", response_model=list[VerificacionTermometroResponse])
def get_historico(
    sede_id: Optional[int] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    query = db.query(VerificacionTermometro)

    if current_user.rol != "administrador":
        if current_user.regional:
            regional_sede_ids = [s.id for s in db.query(Sede).filter(Sede.regional == current_user.regional).all()]
            if regional_sede_ids:
                query = query.filter(VerificacionTermometro.sede_id.in_(regional_sede_ids))
            else:
                query = query.filter(VerificacionTermometro.creado_por == current_user.id)
        else:
            query = query.filter(VerificacionTermometro.creado_por == current_user.id)

    if sede_id:
        query = query.filter(VerificacionTermometro.sede_id == sede_id)
    if fecha_desde:
        query = query.filter(VerificacionTermometro.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(VerificacionTermometro.fecha <= fecha_hasta)

    verificaciones = query.order_by(VerificacionTermometro.fecha.desc()).offset((page - 1) * limit).limit(limit).all()

    results = []
    for v in verificaciones:
        sede = db.query(Sede).filter(Sede.id == v.sede_id).first()
        creador = db.query(Usuario).filter(Usuario.id == v.creado_por).first()
        results.append(_build_response_obj(v, sede, creador))

    return results

@router.get("/{id}", response_model=VerificacionTermometroResponse)
def get_verificacion_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    v = db.query(VerificacionTermometro).filter(VerificacionTermometro.id == id).first()
    if not v:
        raise HTTPException(404, "Verificación no encontrada")
    
    sede = db.query(Sede).filter(Sede.id == v.sede_id).first()
    creador = db.query(Usuario).filter(Usuario.id == v.creado_por).first()
    return _build_response_obj(v, sede, creador)

# ── Generación de PDF FR-CAL-037 ──────────────────────────────────────────────

@router.get("/{id}/pdf")
def download_pdf(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    v = db.query(VerificacionTermometro).filter(VerificacionTermometro.id == id).first()
    if not v:
        raise HTTPException(404, "Verificación no encontrada")
    sede = db.query(Sede).filter(Sede.id == v.sede_id).first()

    buf = _generate_report_pdf(v, sede)
    safe_sede_nombre = _sanitize_filename(sede.nombre)
    filename = f"FR-CAL-037_Verificacion_{safe_sede_nombre}_{v.codigo}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})

# ── Helpers y Generadores Internos ────────────────────────────────────────────

def _build_response_obj(v: VerificacionTermometro, sede: Optional[Sede], creador: Optional[Usuario]) -> VerificacionTermometroResponse:
    from schemas.verificacion_termometro import VerificacionTermometroDetalleResponse
    detalles_resp = []
    for d in v.detalles:
        detalles_resp.append(
            VerificacionTermometroDetalleResponse(
                id=d.id,
                verificacion_id=d.verificacion_id,
                asignado_a=d.asignado_a,
                serial_id=d.serial_id,
                marca_modelo=d.marca_modelo,
                estado_fisico=d.estado_fisico,
                valor_objetivo=float(d.valor_objetivo),
                lectura_verificado=float(d.lectura_verificado) if d.lectura_verificado is not None else None,
                lectura_patron=float(d.lectura_patron) if d.lectura_patron is not None else None,
                correccion=float(d.correccion) if d.correccion is not None else None,
                emp=d.emp,
                firma_realiza=d.firma_realiza,
                aprobado=d.aprobado,
                rechazado=d.rechazado
            )
        )
    
    return VerificacionTermometroResponse(
        id=v.id,
        codigo=v.codigo,
        sede_id=v.sede_id,
        sede_nombre=sede.nombre if sede else None,
        fecha=v.fecha,
        equipo=v.equipo,
        serial_patron=v.serial_patron,
        observaciones=v.observaciones,
        revisado_por=v.revisado_por,
        accion_reajuste=v.accion_reajuste,
        accion_mantenimiento=v.accion_mantenimiento,
        accion_reemplazo=v.accion_reemplazo,
        accion_no_aplica=v.accion_no_aplica,
        creado_por=v.creado_por,
        creador_nombre=creador.nombre_completo if creador else None,
        creado_at=v.creado_at,
        detalles=detalles_resp
    )

def _generate_report_pdf(v: VerificacionTermometro, sede: Sede) -> io.BytesIO:
    buf = io.BytesIO()
    # Printable area: 11.0" - 0.8" = 10.2" width
    # 8.5" - 0.8" = 7.7" height. Using very conservative padding and Spacers to guarantee single-page fit.
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter),
                            leftMargin=0.4*inch, rightMargin=0.4*inch,
                            topMargin=0.4*inch, bottomMargin=0.4*inch)
    story = []

    # 1. Cabecera FR-CAL-037
    header_title_style = _style('HT', fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)
    header_meta_style = _style('HM', fontSize=7.5, fontName='Helvetica', alignment=TA_CENTER)
    
    if os.path.exists(LOGO_PATH):
        logo_img = Image(LOGO_PATH, width=1.6*inch, height=0.45*inch)
        logo_img.hAlign = 'LEFT'
    else:
        logo_img = Paragraph('<font color="#F7941D"><b>R</b></font>'
                             '<font color="#009B3A"><b>RANSA</b></font>',
                             _style('L', fontSize=18, fontName='Helvetica-Bold', textColor=_GREEN))

    title_p = Paragraph('VERIFICACIÓN DE LA CALIBRACIÓN DE TERMÓMETROS', header_title_style)
    subtitle_p = Paragraph('FR-CAL-037', _style('HS', fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER))
    
    header_data = [
        [logo_img, title_p, Paragraph('Versión: 7', header_meta_style)],
        ['', subtitle_p, Paragraph('Página 1 de 1', header_meta_style)]
    ]
    
    header_table = Table(header_data, colWidths=[2.2*inch, 5.8*inch, 2.2*inch])
    header_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (0, 1)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))

    # 2. Información del Equipo, Fecha, Patrón
    info_style = _style('IS', fontSize=7.5, fontName='Helvetica')
    info_data = [
        [
            Paragraph(f"<b>Equipo:</b> {v.equipo or ''}", info_style),
            Paragraph(f"<b>Fecha:</b> {v.fecha.strftime('%d/%m/%Y')}", info_style)
        ],
        [
            Paragraph(f"<b>Serial ID termómetro patrón:</b> {v.serial_patron or ''}", info_style),
            ""
        ]
    ]
    info_table = Table(info_data, colWidths=[6.0*inch, 4.2*inch])
    info_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4))

    # 3. Tabla principal integrada (Nota + headers + datos)
    th_style = _style('TH', fontSize=6.2, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.white, leading=7.5)
    cell_style = _style('CS', fontSize=6.5, fontName='Helvetica', alignment=TA_CENTER, leading=8)
    cell_left_style = _style('CSL', fontSize=6.5, fontName='Helvetica', alignment=TA_LEFT, leading=8)
    
    note_p = Paragraph('<u><b>Nota:</b></u> SI la desviación es mayor al rango definido del +/- 1°C. SI en la inspección física del equipo se evidencia deterioro y/o daño se deben tomar Acciones.', _style('NS', fontSize=7, fontName='Helvetica-Bold'))
    result_title_p = Paragraph('<b>RESULTADO<br/>MARCA CON (X)</b>', _style('RTP', fontSize=6.5, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.white))
    
    row_0 = [note_p, "", "", "", "", "", "", "", "", "", result_title_p, ""]
    row_1 = [
        Paragraph('TERMÓMETRO ASIGNADO A:', th_style),
        Paragraph('SERIAL ID', th_style),
        Paragraph('MARCA / MODELO', th_style),
        Paragraph('ESTADO<br/>FÍSICO', th_style),
        Paragraph('VALOR<br/>OBJETIVO (C°)', th_style),
        Paragraph('LECTURA - IBC<br/>TERMÓMETRO<br/>VERIFICADO', th_style),
        Paragraph('LECTURA - PATRÓN', th_style),
        Paragraph('CORRECCIÓN', th_style),
        Paragraph('EMP<br/>(Error máximo permitido)', th_style),
        Paragraph('FIRMA DE QUIEN REALIZA<br/>LA VERIFICACIÓN', th_style),
        Paragraph('APROBADO', th_style),
        Paragraph('RECHAZADO', th_style)
    ]
    
    table_data = [row_0, row_1]
    
    # Rellenar con los detalles de termómetros
    detalles_list = list(v.detalles)
    
    # Agrupamos por termómetro para aplicar spans
    termometros_agrupados = {}
    for d in detalles_list:
        key = (d.asignado_a or '', d.serial_id or '', d.marca_modelo or '')
        if key not in termometros_agrupados:
            termometros_agrupados[key] = []
        termometros_agrupados[key].append(d)
        
    row_count = 2  # 2 filas para el header
    spans = [
        ('SPAN', (0, 0), (9, 0)),
        ('SPAN', (10, 0), (11, 0)),
    ]
    
    for key, items in termometros_agrupados.items():
        asignado, serial, marca = key
        
        # Estado físico del termómetro (mismo para ambas lecturas)
        estado_fisico_val = ''
        for x in items:
            if hasattr(x, 'estado_fisico') and x.estado_fisico:
                estado_fisico_val = x.estado_fisico
                break
        
        # Debemos garantizar que haya lecturas para -18 y 0.
        item_18 = next((x for x in items if float(x.valor_objetivo) == -18.0), None)
        item_0 = next((x for x in items if float(x.valor_objetivo) == 0.0), None)
        
        if not item_18:
            item_18 = VerificacionTermometroDetalle(valor_objetivo=-18)
        if not item_0:
            item_0 = VerificacionTermometroDetalle(valor_objetivo=0)
            
        for d in [item_18, item_0]:
            correccion_str = format_correction(d.correccion)
            table_data.append([
                Paragraph(asignado, cell_left_style),
                Paragraph(serial, cell_style),
                Paragraph(marca, cell_style),
                Paragraph(estado_fisico_val, cell_style),
                Paragraph(f"{int(d.valor_objetivo)}", cell_style),
                Paragraph(format_reading(d.lectura_verificado), cell_style),
                Paragraph(format_reading(d.lectura_patron), cell_style),
                Paragraph(correccion_str, cell_style),
                Paragraph(d.emp or '±1', cell_style),
                Paragraph(d.firma_realiza or '', cell_style),
                Paragraph('X' if d.aprobado else '', cell_style),
                Paragraph('X' if d.rechazado else '', cell_style)
            ])
        
        # Aplicar spans verticales para este par de renglones
        spans.append(('SPAN', (0, row_count), (0, row_count + 1)))
        spans.append(('SPAN', (1, row_count), (1, row_count + 1)))
        spans.append(('SPAN', (2, row_count), (2, row_count + 1)))
        spans.append(('SPAN', (3, row_count), (3, row_count + 1)))
        spans.append(('SPAN', (9, row_count), (9, row_count + 1)))
        row_count += 2

    # Rellenar con filas vacías para mantener consistencia visual (mínimo 12 filas de datos, 6 termómetros)
    while len(table_data) < 14:
        # Fila para -18
        table_data.append([
            Paragraph('', cell_left_style), Paragraph('', cell_style), Paragraph('', cell_style),
            Paragraph('', cell_style),
            Paragraph('-18', cell_style), Paragraph('', cell_style), Paragraph('', cell_style),
            Paragraph('', cell_style), Paragraph('±1', cell_style), Paragraph('', cell_style),
            Paragraph('', cell_style), Paragraph('', cell_style)
        ])
        # Fila para 0
        table_data.append([
            Paragraph('', cell_left_style), Paragraph('', cell_style), Paragraph('', cell_style),
            Paragraph('', cell_style),
            Paragraph('0', cell_style), Paragraph('', cell_style), Paragraph('', cell_style),
            Paragraph('', cell_style), Paragraph('±1', cell_style), Paragraph('', cell_style),
            Paragraph('', cell_style), Paragraph('', cell_style)
        ])
        spans.append(('SPAN', (0, row_count), (0, row_count + 1)))
        spans.append(('SPAN', (1, row_count), (1, row_count + 1)))
        spans.append(('SPAN', (2, row_count), (2, row_count + 1)))
        spans.append(('SPAN', (3, row_count), (3, row_count + 1)))
        spans.append(('SPAN', (9, row_count), (9, row_count + 1)))
        row_count += 2

    # ColWidths: total exactamente 10.2 inches (12 columnas), aligned with the other tables
    widths = [1.4*inch, 0.7*inch, 1.0*inch, 0.7*inch, 0.55*inch, 0.75*inch, 0.75*inch, 0.7*inch, 0.55*inch, 1.4*inch, 0.65*inch, 0.65*inch]
    
    t = Table(table_data, colWidths=widths, repeatRows=2)
    
    t_style_cmds = [
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        
        # Row 0: Note spans and Result backgrounds
        ('BACKGROUND', (10, 0), (11, 0), _GREEN),
        
        # Row 1: Header backgrounds
        ('BACKGROUND', (0, 1), (3, 1), _ORANGE),
        ('BACKGROUND', (4, 1), (4, 1), _GREEN),
        ('BACKGROUND', (5, 1), (8, 1), _ORANGE),
        ('BACKGROUND', (9, 1), (9, 1), _GREEN),
        ('BACKGROUND', (10, 1), (11, 1), _ORANGE),
    ]
    
    # Alternar fondos de filas de datos
    for r in range(2, len(table_data)):
        if (r - 2) % 4 in (0, 1):  # Agrupación de dos en dos por termómetro
            t_style_cmds.append(('BACKGROUND', (0, r), (-1, r), _STRIPE))
            
    t.setStyle(TableStyle(t_style_cmds + spans))
    story.append(t)
    story.append(Spacer(1, 4))

    # 5. Sección de Acciones y Firma
    chk_reajuste = "[X]" if v.accion_reajuste else "[  ]"
    chk_mant = "[X]" if v.accion_mantenimiento else "[  ]"
    chk_reemp = "[X]" if v.accion_reemplazo else "[  ]"
    chk_no_aplica = "[X]" if v.accion_no_aplica else "[  ]"
    
    actions_header_p = Paragraph("<b>Acciones en caso de desviación</b>", _style('AHP', fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white))
    revisado_header_p = Paragraph("<b>Revisado y Aprobado por:</b>", _style('RHP', fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white))
    
    actions_body_p = Paragraph(
        f"{chk_reajuste} Reajuste de termómetro verificado<br/>"
        f"{chk_mant} Envío a mantenimiento y calibración externa<br/>"
        f"{chk_reemp} Reemplazo del equipo<br/>"
        f"{chk_no_aplica} No aplican acciones por desviación",
        _style('ABP', fontSize=7, fontName='Helvetica', leading=10)
    )
    
    revisado_body_p = Paragraph(
        f"<br/>"
        f"______________________________________<br/>"
        f"{v.revisado_por or ''}",
        _style('RBP', fontSize=7.5, fontName='Helvetica', leading=11, alignment=TA_CENTER)
    )
    
    bottom_cols_data = [
        [actions_header_p, revisado_header_p],
        [actions_body_p, revisado_body_p]
    ]
    
    # 7.2" left + 3.0" right = 10.2" total width to align perfectly with cols 0-7 vs 8-10 of main table
    bottom_table = Table(bottom_cols_data, colWidths=[7.2*inch, 3.0*inch])
    bottom_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), _GREEN),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(bottom_table)
    story.append(Spacer(1, 4))
    
    # 6. Observaciones
    obs_label_p = Paragraph("<b>Observaciones específicas de algún equipo: (cite el número de serial)</b>", _style('OL', fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white))
    obs_text_p = Paragraph(v.observaciones or "Sin observaciones.", _style('OT', fontSize=7, fontName='Helvetica', leading=9))
    
    obs_table_data = [
        [obs_label_p],
        [obs_text_p]
    ]
    obs_table = Table(obs_table_data, colWidths=[10.2*inch])
    obs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), _GREEN),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(obs_table)

    doc.build(story)
    buf.seek(0)
    return buf

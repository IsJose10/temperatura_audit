import io
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch, mm
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

LOGO_PATH = os.path.join("static", "img", "ransa_logo_wide.png")


def _build_ransa_logo_table():
    """Build a header with RANSA branding matching FR-CAL-032 format using original logo."""
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        leading=14
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        alignment=TA_CENTER
    )
    version_style = ParagraphStyle(
        'Version', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica',
        alignment=TA_CENTER
    )

    # Use the original Ransa logo PNG
    if os.path.exists(LOGO_PATH):
        logo_img = Image(LOGO_PATH, width=1.8 * inch, height=0.5 * inch)
        logo_img.hAlign = 'LEFT'
    else:
        # Fallback to text if image not found
        logo_style = ParagraphStyle(
            'RansaLogo', parent=styles['Normal'],
            fontSize=18, fontName='Helvetica-Bold',
            textColor=colors.HexColor('#009B3A'),
            alignment=TA_LEFT
        )
        logo_img = Paragraph(
            '<font color="#F7941D"><b>R</b></font><font color="#009B3A"><b>RANSA</b></font>',
            logo_style
        )

    title_text = Paragraph('CONTROL DE TEMPERATURAS<br/>CÁMARAS DE ALMACENAMIENTO', title_style)
    version_text = Paragraph('Versión: 7', version_style)
    code_text = Paragraph('FR-CAL-032', sub_style)

    header_data = [[logo_img, title_text, version_text], ['', code_text, '']]

    header_table = Table(header_data, colWidths=[2 * inch, 5.5 * inch, 2 * inch])
    header_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (0, 1)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    return header_table


def _build_manual_section():
    """Build a section for manual handwritten entries: Tablero and Temperatura Manual."""
    styles = getSampleStyleSheet()

    section_title = ParagraphStyle(
        'ManualTitle', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.white
    )
    cell_style = ParagraphStyle(
        'ManualCell', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica-Bold',
        alignment=TA_CENTER
    )

    ransa_dark = colors.HexColor('#004A1B')

    # Header row
    header_row = [
        Paragraph('TABLERO', section_title),
        Paragraph('TEMPERATURA MANUAL', section_title),
    ]

    # 6 empty rows for handwriting
    table_data = [header_row]
    for _ in range(6):
        table_data.append(['', ''])

    manual_table = Table(table_data, colWidths=[4.75 * inch, 4.75 * inch])
    manual_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), ransa_dark),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Grid
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        # Row height for writing space
        ('TOPPADDING', (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
    ]))

    return manual_table


def _format_range(rango_str):
    """Return a short range label."""
    if rango_str and rango_str != "No definido":
        return f"({rango_str})"
    return ""


def _generate_pdf(auditoria, sede, detalles_with_cameras, db):
    """Generate the FR-CAL-032 formatted PDF and return bytes."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.5 * inch,
    )

    elements = []
    styles = getSampleStyleSheet()

    # --- Header ---
    elements.append(_build_ransa_logo_table())
    elements.append(Spacer(1, 8))

    # --- Responsible / Date row ---
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=8, fontName='Helvetica')
    info_bold = ParagraphStyle('InfoBold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')

    fecha = auditoria.fecha or datetime.now()
    dia = fecha.strftime('%d')
    mes = fecha.strftime('%m')
    anio = fecha.strftime('%Y')

    # Extract all unique auditors
    auditors = set()
    if auditoria.nombre_auditor:
        auditors.add(auditoria.nombre_auditor)
    for detalle, camara in detalles_with_cameras:
        if detalle.nombre_auditor:
            auditors.add(detalle.nombre_auditor)
            
    responsables_text = " / ".join(auditors)

    responsible_data = [
        [
            Paragraph(f'<b>Responsables:</b> {responsables_text}', info_style),
            Paragraph(f'<b>Sede:</b> {sede.nombre}', info_style),
            Paragraph(f'<b>Día</b> {dia}  <b>mes</b> {mes}  <b>año</b> {anio}', info_style),
        ]
    ]
    resp_table = Table(responsible_data, colWidths=[3.3 * inch, 3.2 * inch, 3 * inch])
    resp_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(resp_table)
    elements.append(Spacer(1, 6))

    # --- Main data table ---
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7, fontName='Helvetica', leading=9)
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER, leading=9, textColor=colors.white)

    col_headers = ['Cámara', 'Rango\nEsperado', 'Temp\nProducto °C', 'Temp\nPasillo °C', 'Hora', 'Producto', 'Observaciones', 'Tablero', 'Temp.\nManual']
    header_row = [Paragraph(h.replace('\n', '<br/>'), header_style) for h in col_headers]

    table_data = [header_row]

    ransa_green = colors.HexColor('#009B3A')
    ransa_dark = colors.HexColor('#064e3b')

    for detalle, camara in detalles_with_cameras:
        cumplimiento = verificar_cumplimiento(
            sede.nombre,
            camara.nombre if camara else "",
            float(detalle.temperatura) if detalle.temperatura is not None else 0
        )
        rango_str = cumplimiento["rango"]

        temp_str = f'{float(detalle.temperatura):.1f}°C' if detalle.temperatura is not None else ''
        temp_pasillo_str = f'{float(detalle.temperatura_pasillo):.1f}°C' if detalle.temperatura_pasillo is not None else ''
        hora_str = detalle.hora_registro.strftime('%H:%M') if detalle.hora_registro else ''
        producto_str = detalle.nombre_producto or ''
        obs_str = detalle.observaciones or ''
        camara_nombre = camara.nombre if camara else f'Cámara {detalle.camara_id}'

        row = [
            Paragraph(camara_nombre, cell_style),
            Paragraph(rango_str, cell_style),
            Paragraph(temp_str, cell_style),
            Paragraph(temp_pasillo_str, cell_style),
            Paragraph(hora_str, cell_style),
            Paragraph(producto_str, cell_style),
            Paragraph(obs_str, cell_style),
            '',  # Tablero (empty for handwriting)
            '',  # Temp. Manual (empty for handwriting)
        ]
        table_data.append(row)

    # Add empty rows if less than 9 to keep a consistent look
    while len(table_data) < 10:
        table_data.append([''] * 9)

    col_widths = [1.4 * inch, 0.8 * inch, 0.7 * inch, 0.7 * inch, 0.5 * inch, 1.1 * inch, 1.7 * inch, 0.85 * inch, 0.75 * inch]
    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table_style_cmds = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), ransa_dark),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Grid
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]

    # Alternate row colors (no compliance coloring)
    for i in range(len(table_data) - 1):
        row_idx = i + 1
        if row_idx < len(table_data) and i % 2 == 0:
            table_style_cmds.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#f8faf8')))

    main_table.setStyle(TableStyle(table_style_cmds))
    elements.append(main_table)
    elements.append(Spacer(1, 10))

    # --- Observations ---
    obs_style = ParagraphStyle('Obs', parent=styles['Normal'], fontSize=8, fontName='Helvetica', leading=10)
    obs_bold = ParagraphStyle('ObsBold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', leading=10)

    # Collect all observations
    all_obs = []
    for detalle, camara in detalles_with_cameras:
        if detalle.observaciones:
            c_name = camara.nombre if camara else f'Cámara {detalle.camara_id}'
            all_obs.append(f"<b>{c_name}:</b> {detalle.observaciones}")

    obs_text = '<br/>'.join(all_obs) if all_obs else 'Sin observaciones.'

    obs_data = [
        [Paragraph('<b>Observaciones:</b>', obs_bold)],
        [Paragraph(obs_text, obs_style)],
    ]
    obs_table = Table(obs_data, colWidths=[9.5 * inch])
    obs_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(obs_table)
    elements.append(Spacer(1, 14))

    # --- Signatures with auditor names ---
    sign_style = ParagraphStyle('Sign', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')
    sign_name_style = ParagraphStyle('SignName', parent=styles['Normal'], fontSize=8, fontName='Helvetica', alignment=TA_CENTER)
    sign_line = '_' * 40

    sign_data = [
        [
            Paragraph(f'<b>Realizado por:</b> {sign_line}', sign_style),
            Paragraph(f'<b>Revisado por:</b> {sign_line}', sign_style),
        ],
        [
            Paragraph(responsables_text, sign_name_style),
            Paragraph('', sign_name_style),
        ]
    ]
    sign_table = Table(sign_data, colWidths=[4.75 * inch, 4.75 * inch])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
    ]))
    elements.append(sign_table)

    # Build
    doc.build(elements)
    buffer.seek(0)
    return buffer


@router.get("/auditorias/{auditoria_id}/pdf")
def download_pdf(
    auditoria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    auditoria = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not auditoria:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    sede = db.query(Sede).filter(Sede.id == auditoria.sede_id).first()
    if not sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    # Get all detalles with camera info
    detalles = db.query(AuditoriaDetalle).filter(
        AuditoriaDetalle.auditoria_id == auditoria.id
    ).all()

    detalles_with_cameras = []
    for d in detalles:
        camara = db.query(Camara).filter(Camara.id == d.camara_id).first()
        detalles_with_cameras.append((d, camara))

    pdf_buffer = _generate_pdf(auditoria, sede, detalles_with_cameras, db)

    filename = f"FR-CAL-032_{sede.nombre}_{auditoria.id_auditoria}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/auditorias/{auditoria_id}/cumplimiento")
def get_cumplimiento(
    auditoria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Returns compliance status for all cameras in an audit."""
    auditoria = db.query(Auditoria).filter(Auditoria.id == auditoria_id).first()
    if not auditoria:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    sede = db.query(Sede).filter(Sede.id == auditoria.sede_id).first()
    if not sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    detalles = db.query(AuditoriaDetalle).filter(
        AuditoriaDetalle.auditoria_id == auditoria.id
    ).all()

    results = []
    total = len(detalles)
    cumple_count = 0
    no_cumple_count = 0

    for d in detalles:
        camara = db.query(Camara).filter(Camara.id == d.camara_id).first()
        camara_nombre = camara.nombre if camara else f"Cámara {d.camara_id}"

        if d.temperatura is not None:
            check = verificar_cumplimiento(sede.nombre, camara_nombre, float(d.temperatura))
        else:
            check = {"cumple": None, "rango": "No definido", "mensaje": "Sin temperatura registrada"}

        if check["cumple"] is True:
            cumple_count += 1
        elif check["cumple"] is False:
            no_cumple_count += 1

        results.append({
            "camara_id": d.camara_id,
            "camara_nombre": camara_nombre,
            "temperatura": float(d.temperatura) if d.temperatura is not None else None,
            "cumple": check["cumple"],
            "rango": check["rango"],
            "mensaje": check["mensaje"],
        })

    return {
        "auditoria_id": auditoria.id,
        "sede_nombre": sede.nombre,
        "total_camaras": total,
        "en_cumplimiento": cumple_count,
        "fuera_de_rango": no_cumple_count,
        "detalles": results
    }

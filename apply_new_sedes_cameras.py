"""
Script: Agregar sedes y cámaras nuevas
Fecha: 2026-03-26
Descripción: Crea las sedes Fontibón, Pereira y Funza con sus cámaras reales.
             Actualiza las cámaras de Cali (reemplaza genéricas por reales).
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara
from models.usuario import Usuario  # Needed for relationship resolution
from models.auditoria import Auditoria, AuditoriaDetalle


# =============================================
# Definición de sedes y cámaras
# =============================================

NUEVAS_SEDES = {
    "Fontibón": {
        "codigo": "FON",
        "regional": "Centro",
        "camaras": [
            ("1", "Congelada"),
            ("2", "Congelada"),
            ("3", "Congelada"),
            ("5", "Congelada"),
            ("7", "Congelada"),
            ("10", "Congelada"),
            ("11", "Congelada"),
            ("15", "Congelada"),
            ("16", "Congelada"),
            ("17", "Congelada"),
            ("A01", "Refrigerada"),
            ("Devoluciones", "Refrigerada"),
            ("Prec. A01", "Refrigerada"),
            ("Bahía A01", "Refrigerada"),
            ("Pre Cong. 10 y 11", "Congelada"),
            ("Pre Refrig.", "Refrigerada"),
            ("Pre Cong.1", "Congelada"),
            ("Bahía OPL", "Refrigerada"),
        ],
    },
    "Pereira": {
        "codigo": "PER",
        "regional": "Eje Cafetero",
        "camaras": [
            ("Contenedor #1", "Congelada"),
            ("Contenedor #2", "Congelada"),
            ("Contenedor #3", "Congelada"),
            ("Contenedor #4", "Congelada"),
            ("Cava Refrigerado", "Refrigerada"),
        ],
    },
    "Funza": {
        "codigo": "FNZ",
        "regional": "Centro",
        "camaras": [
            ("Precámara de refrigeración", "Refrigerada"),
            ("Cámara de refrigeración", "Refrigerada"),
            ("Pre-cámara de congelación", "Congelada"),
            ("Cámara de congelación 1 (RICH'S)", "Congelada"),
            ("Cámara de congelación 2 (ANTILLANA)", "Congelada"),
            ("Túnel de Congelación #1", "Congelada"),
            ("Túnel de Congelación #2 (RICH'S)", "Congelada"),
        ],
    },
}

CAMARAS_CALI = [
    ("Precámara de fruver", "Refrigerada"),
    ("Cámara de fruver 1", "Refrigerada"),
    ("Cámara de refrigerado 1", "Refrigerada"),
    ("Cámara de refrigerado 2", "Refrigerada"),
    ("Precámara de refrigerado", "Refrigerada"),
    ("Cámara de congelado 1", "Congelada"),
    ("Cámara de congelado 2", "Congelada"),
    ("Cámara de congelado 3", "Congelada"),
]


def apply_changes():
    db = SessionLocal()
    try:
        # ---- 1. Crear sedes nuevas (Fontibón, Pereira, Funza) ----
        for nombre_sede, info in NUEVAS_SEDES.items():
            sede = db.query(Sede).filter(Sede.codigo == info["codigo"]).first()
            if not sede:
                sede = Sede(
                    nombre=nombre_sede,
                    codigo=info["codigo"],
                    regional=info["regional"],
                )
                db.add(sede)
                db.flush()
                print(f"\n[+] Sede creada: {nombre_sede} ({info['codigo']}) - Regional: {info['regional']}")
            else:
                print(f"\n[=] Sede ya existe: {nombre_sede} ({info['codigo']})")
                # Limpiar cámaras existentes (eliminar auditorías vinculadas primero)
                auditorias = db.query(Auditoria).filter(Auditoria.sede_id == sede.id).all()
                for aud in auditorias:
                    db.query(AuditoriaDetalle).filter(AuditoriaDetalle.auditoria_id == aud.id).delete()
                    db.delete(aud)
                db.commit()
                db.query(Camara).filter(Camara.sede_id == sede.id).delete()
                db.commit()

            for cam_nombre, cam_tipo in info["camaras"]:
                camara = Camara(nombre=cam_nombre, sede_id=sede.id, tipo=cam_tipo, activo=True)
                db.add(camara)
                print(f"    + {cam_nombre} ({cam_tipo})")

        # ---- 2. Actualizar cámaras de Cali ----
        cali = db.query(Sede).filter(Sede.codigo == "CAL").first()
        if cali:
            print(f"\n[~] Actualizando cámaras de Cali...")
            # Limpiar auditorías y cámaras existentes
            auditorias = db.query(Auditoria).filter(Auditoria.sede_id == cali.id).all()
            for aud in auditorias:
                db.query(AuditoriaDetalle).filter(AuditoriaDetalle.auditoria_id == aud.id).delete()
                db.delete(aud)
            db.commit()
            db.query(Camara).filter(Camara.sede_id == cali.id).delete()
            db.commit()

            for cam_nombre, cam_tipo in CAMARAS_CALI:
                camara = Camara(nombre=cam_nombre, sede_id=cali.id, tipo=cam_tipo, activo=True)
                db.add(camara)
                print(f"    + {cam_nombre} ({cam_tipo})")
        else:
            print("\n[!] Sede Cali (CAL) no encontrada. Creándola...")
            cali = Sede(nombre="Cali", codigo="CAL", regional="Pacífico")
            db.add(cali)
            db.flush()
            for cam_nombre, cam_tipo in CAMARAS_CALI:
                camara = Camara(nombre=cam_nombre, sede_id=cali.id, tipo=cam_tipo, activo=True)
                db.add(camara)
                print(f"    + {cam_nombre} ({cam_tipo})")

        db.commit()
        print("\n" + "=" * 50)
        print("[OK] Todas las sedes y cámaras actualizadas con éxito!")
        print("=" * 50)

        # ---- 3. Verificación ----
        print("\n--- Resumen ---")
        all_codes = [info["codigo"] for info in NUEVAS_SEDES.values()] + ["CAL"]
        for code in all_codes:
            sede = db.query(Sede).filter(Sede.codigo == code).first()
            if sede:
                count = db.query(Camara).filter(Camara.sede_id == sede.id, Camara.activo == True).count()
                print(f"  {sede.nombre} ({sede.codigo}) - Regional: {sede.regional} - Cámaras: {count}")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    apply_changes()

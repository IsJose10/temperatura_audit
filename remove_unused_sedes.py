"""
Script: Eliminar sedes no necesarias
Fecha: 2026-03-26
Descripción: Elimina Medellín, Bogotá y Barranquilla (y sus cámaras/auditorías).
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara
from models.usuario import Usuario
from models.auditoria import Auditoria, AuditoriaDetalle

SEDES_TO_REMOVE = ["MED", "BOG", "BAQ"]


def remove_sedes():
    db = SessionLocal()
    try:
        for codigo in SEDES_TO_REMOVE:
            sede = db.query(Sede).filter(Sede.codigo == codigo).first()
            if not sede:
                print(f"[=] Sede {codigo} no existe, saltando...")
                continue

            print(f"\n[-] Eliminando sede: {sede.nombre} ({sede.codigo})")

            # Delete audit details and audits
            auditorias = db.query(Auditoria).filter(Auditoria.sede_id == sede.id).all()
            for aud in auditorias:
                count = db.query(AuditoriaDetalle).filter(
                    AuditoriaDetalle.auditoria_id == aud.id
                ).delete()
                print(f"    - {count} detalles eliminados de auditoria {aud.id_auditoria}")
                db.delete(aud)

            # Delete cameras
            cam_count = db.query(Camara).filter(Camara.sede_id == sede.id).delete()
            print(f"    - {cam_count} camaras eliminadas")

            # Delete sede
            db.delete(sede)
            print(f"    [OK] Sede {sede.nombre} eliminada")

        db.commit()

        print("\n" + "=" * 50)
        print("[OK] Sedes eliminadas exitosamente!")
        print("=" * 50)

        # Verify remaining
        print("\n--- Sedes restantes ---")
        for sede in db.query(Sede).filter(Sede.activo == True).all():
            cam_count = db.query(Camara).filter(Camara.sede_id == sede.id).count()
            print(f"  {sede.nombre} ({sede.codigo}) - Regional: {sede.regional} - Camaras: {cam_count}")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    remove_sedes()

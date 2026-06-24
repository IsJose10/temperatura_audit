"""Migración: Agregar cámara Bahía a la sede Cali."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara

def apply():
    db = SessionLocal()
    try:
        sede = db.query(Sede).filter(Sede.codigo == "CAL").first()
        if not sede:
            print("[!] Sede Cali (CAL) no encontrada"); return

        exists = db.query(Camara).filter(
            Camara.sede_id == sede.id, Camara.nombre == "Bahía"
        ).first()
        if exists:
            print("[=] Cámara Bahía ya existe en Cali"); return

        db.add(Camara(nombre="Bahía", sede_id=sede.id, tipo="Refrigerada", activo=True))
        db.commit()
        print("[OK] Cámara Bahía agregada a Cali.")
    except Exception as e:
        db.rollback(); print(f"[ERROR] {e}"); raise
    finally:
        db.close()

if __name__ == "__main__":
    apply()

"""
Agrega la cámara 8 (Ambiente, max 25°C) a la sede Fontibón.
La cámara 16 (Ambiente) y Maquila (0-4°C) ya existen.

Ejecutar: python add_fontibon_camera8.py
"""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara

def add_camera():
    db = SessionLocal()
    try:
        fontibon = db.query(Sede).filter(Sede.nombre == "Fontibón").first()
        if not fontibon:
            print("[ERROR] Sede Fontibón no encontrada")
            return

        existing = db.query(Camara).filter(
            Camara.sede_id == fontibon.id, Camara.nombre == "8"
        ).first()
        if existing:
            print("[=] Cámara 8 ya existe en Fontibón")
        else:
            db.add(Camara(nombre="8", sede_id=fontibon.id, tipo="Refrigerada", activo=True))
            db.commit()
            print("[+] Cámara 8 agregada a Fontibón (Ambiente, max 25°C)")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_camera()

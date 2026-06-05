import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara

def apply_changes():
    db = SessionLocal()
    try:
        # Check if already exists
        sede = db.query(Sede).filter(Sede.codigo == "CLD").first()
        if not sede:
            sede = Sede(
                nombre="Caldas",
                codigo="CLD",
                regional="Medellin",
            )
            db.add(sede)
            db.commit()
            print("[+] Sede creada: Caldas (CLD) - Regional: Medellin")
        else:
            print(f"[=] Sede ya existe: Caldas (CLD) - Regional: {sede.regional}")
            # Ensure regional is correct
            if sede.regional != "Medellin":
                sede.regional = "Medellin"
                db.commit()
                print("[~] Regional actualizada a: Medellin")
        
        # Clean up existing cameras to prevent duplicates/stale cameras
        db.query(Camara).filter(Camara.sede_id == sede.id).delete()
        db.commit()

        # Insert new cameras
        cameras_list = [
            ("PRECAVA DE CONGELADO", "Congelada"),
            ("PRECAV DE REFRIGERADO", "Refrigerada"),
            ("CONVER 1", "Congelada"),
            ("CONGELADOS 2", "Congelada"),
            ("CONGELADOS 1", "Congelada"),
            ("CONVER 2", "Refrigerada"),
            ("FRISBY REFRIGERADO", "Refrigerada"),
        ]
        for name, cam_type in cameras_list:
            camara = Camara(nombre=name, sede_id=sede.id, tipo=cam_type, activo=True)
            db.add(camara)
        db.commit()
        print(f"[+] {len(cameras_list)} cámaras registradas con éxito en Caldas.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    apply_changes()

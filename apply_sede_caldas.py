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
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    apply_changes()

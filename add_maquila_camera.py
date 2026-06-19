import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara

# ponytail: simple database camera adder
def add_camera():
    db = SessionLocal()
    try:
        # Find Fontibón Sede
        fontibon = db.query(Sede).filter(Sede.nombre == "Fontibón").first()
        if not fontibon:
            print("[ERROR] Sede Fontibón no encontrada")
            return
        
        # Check if Maquila camera already exists
        maquila = db.query(Camara).filter(Camara.sede_id == fontibon.id, Camara.nombre == "Maquila").first()
        if not maquila:
            maquila = Camara(
                nombre="Maquila",
                sede_id=fontibon.id,
                tipo="Refrigerada",
                activo=True
            )
            db.add(maquila)
            db.commit()
            print("[+] Cámara Maquila agregada exitosamente a la sede Fontibón.")
        else:
            print("[=] La cámara Maquila ya existe en la sede Fontibón.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_camera()

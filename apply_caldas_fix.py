"""Migración: Renombrar cámaras de Caldas (sin borrar auditorías) y agregar las 2 faltantes."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara

# viejo_nombre → (nuevo_nombre, nuevo_tipo)
RENAMES = {
    "PRECAVA DE CONGELADO":  ("CAVA CONGELADOS 1", "Congelada"),
    "PRECAV DE REFRIGERADO": ("CAVA REFRIGERADOS 1", "Refrigerada"),
    "CONGELADOS 1":          ("CAVA CONGELADOS 2", "Congelada"),
    "CONGELADOS 2":          ("CAVA REFRIGERADOS 2", "Refrigerada"),
    "CONVER 1":              ("CONVER 1", "Congelada"),
    "CONVER 2":              ("CONVER 2", "Congelada"),
    "FRISBY REFRIGERADO":    ("CAVA REFRIGERADOS 3", "Refrigerada"),
}

NEW_CAMERAS = [
    ("CAVA MAQUILA", "Refrigerada"),
    ("CAVA FRUVER CENCOSUD", "Refrigerada"),
]

def apply():
    db = SessionLocal()
    try:
        sede = db.query(Sede).filter(Sede.codigo == "CLD").first()
        if not sede:
            print("[!] Sede Caldas (CLD) no encontrada"); return

        # Renombrar existentes
        for old_name, (new_name, new_tipo) in RENAMES.items():
            cam = db.query(Camara).filter(Camara.sede_id == sede.id, Camara.nombre == old_name).first()
            if cam:
                cam.nombre = new_name
                cam.tipo = new_tipo
                print(f"  [~] {old_name} → {new_name} ({new_tipo})")
            else:
                print(f"  [?] No encontrada: {old_name}, se omite")

        # Agregar nuevas
        for name, tipo in NEW_CAMERAS:
            exists = db.query(Camara).filter(Camara.sede_id == sede.id, Camara.nombre == name).first()
            if not exists:
                db.add(Camara(nombre=name, sede_id=sede.id, tipo=tipo, activo=True))
                print(f"  [+] {name} ({tipo})")
            else:
                print(f"  [=] Ya existe: {name}")

        db.commit()
        total = db.query(Camara).filter(Camara.sede_id == sede.id, Camara.activo == True).count()
        print(f"[OK] Caldas actualizada. Total cámaras: {total}")
    except Exception as e:
        db.rollback(); print(f"[ERROR] {e}"); raise
    finally:
        db.close()

if __name__ == "__main__":
    apply()

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.sede import Sede
from models.camara import Camara
from models.usuario import Usuario  # Need this for the relationship to work
from models.auditoria import Auditoria, AuditoriaDetalle

def update_galapa_cameras():
    db = SessionLocal()
    try:
        galapa = db.query(Sede).filter(Sede.codigo == "GAL").first()
        if not galapa:
            return
            
        print(f"Sede: {galapa.nombre}")
        
        # We need to drop auditoria records for GAL to be able to delete cameras
        auditorias = db.query(Auditoria).filter(Auditoria.sede_id == galapa.id).all()
        for aud in auditorias:
            db.query(AuditoriaDetalle).filter(AuditoriaDetalle.auditoria_id == aud.id).delete()
            db.delete(aud)
            
        db.commit()
        
        db.query(Camara).filter(Camara.sede_id == galapa.id).delete()
        
        camaras_galapa = [
            ("Pasillo 403", "Refrigerada"),
            ("Pasillo 402", "Refrigerada"),
            ("Pasillo 401", "Refrigerada"),
            ("Pasillo 301", "Refrigerada"),
            ("Pasillo 201", "Refrigerada"),
            ("Pasillo 101", "Refrigerada"),
            ("Precava Refrigerado", "Refrigerada"),
            ("Precava Congelado", "Congelada"),
            ("Bahía", "Refrigerada"),
        ]
        
        for nombre, tipo in camaras_galapa:
            camara = Camara(nombre=nombre, sede_id=galapa.id, tipo=tipo, activo=True)
            db.add(camara)
            print(f"+ {nombre}")
            
        db.commit()
        print("\n¡Cámaras de Galapa actualizadas con éxito!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_galapa_cameras()

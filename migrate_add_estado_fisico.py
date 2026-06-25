"""
migrate_add_estado_fisico.py
----------------------------
Agrega la columna 'estado_fisico' a la tabla verificacion_termometro_detalles.
Ejecutar una sola vez: python migrate_add_estado_fisico.py
"""
import psycopg
from config import DATABASE_URL

def migrate():
    # ponytail: convert SQLAlchemy URL to psycopg-compatible
    conn_url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    
    conn = psycopg.connect(conn_url, autocommit=True)
    cur = conn.cursor()
    
    # Check if column already exists
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'verificacion_termometro_detalles' 
        AND column_name = 'estado_fisico'
    """)
    
    if cur.fetchone():
        print("[OK] Columna 'estado_fisico' ya existe. No se requiere migración.")
    else:
        cur.execute("""
            ALTER TABLE verificacion_termometro_detalles 
            ADD COLUMN estado_fisico VARCHAR(20)
        """)
        print("[OK] Columna 'estado_fisico' agregada exitosamente.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    migrate()

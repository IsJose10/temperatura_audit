import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL
import os

def init_database():
    """Create database ONLY in local."""
    try:
        conn = psycopg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="1015",
            dbname="postgres",
            autocommit=True
        )
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'temperatura_audit'")
        if not cur.fetchone():
            cur.execute('CREATE DATABASE "temperatura_audit"')
            print("[OK] DB creada")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] {e}")

# SOLO LOCAL
if not os.getenv("DATABASE_URL"):
    init_database()

# 🔥 ENGINE con pool optimizado para uso simultáneo multi-dispositivo
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=3,           # Render Free Tier: max ~25 conexiones totales
    max_overflow=7,        # Total máximo: 10 conexiones (seguro para plan gratuito)
    pool_pre_ping=True,    # Detecta conexiones rotas antes de usarlas
    pool_recycle=1800,     # Recicla conexiones cada 30 min (Render cierra idle ~10 min)
    pool_timeout=30,       # Max 30s esperando conexión (evita fallo rápido bajo carga)
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
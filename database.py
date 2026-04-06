import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL
import os


def init_database():
    """Create the database if it does not exist (ONLY LOCAL)."""
    try:
        conn = psycopg.connect(
            DATABASE_URL,
            autocommit=True
        )
        conn.close()
        print("[OK] Conexión local verificada.")
    except Exception as e:
        print(f"[ERROR] Error de conexión: {e}")
        raise


# ✅ SOLO LOCAL (cuando NO hay DATABASE_URL de Render)
if os.getenv("DATABASE_URL") is None:
    init_database()


# ✅ ENGINE (sirve tanto local como Render)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"sslmode": "require"}  # Render necesita SSL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
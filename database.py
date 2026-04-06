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

# 🔥 ENGINE CORRECTO
engine = create_engine(
    DATABASE_URL,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
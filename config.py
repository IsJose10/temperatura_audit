import os

# 🔥 PRIORIDAD: usar DATABASE_URL de Render
DATABASE_URL = os.getenv("DATABASE_URL")

# SOLO si estás en local (fallback)
if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "1015")
    DB_NAME = os.getenv("DB_NAME", "temperatura_audit")

    DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # 🔥 MUY IMPORTANTE: adaptar URL de Render a SQLAlchemy
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "ransa-temperatura-audit-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480 
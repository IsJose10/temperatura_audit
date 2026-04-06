import os

# ✅ USAR DATABASE_URL DE RENDER SI EXISTE
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ SOLO PARA USO LOCAL (fallback)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1015")
DB_NAME = os.getenv("DB_NAME", "temperatura_audit")

# ✅ SI NO EXISTE DATABASE_URL (LOCAL), LA CONSTRUYE
if not DATABASE_URL:
    DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "ransa-temperatura-audit-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480
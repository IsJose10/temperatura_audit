import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def init_database():
    """Create the database if it does not exist."""
    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres",
            autocommit=True
        )
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"[OK] Base de datos '{DB_NAME}' creada exitosamente.")
        else:
            print(f"[OK] Base de datos '{DB_NAME}' ya existe.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Error al crear la base de datos: {e}")
        raise


# Initialize database
init_database()

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

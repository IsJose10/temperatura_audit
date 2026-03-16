from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

import os

from database import Base, engine, SessionLocal
from models.usuario import Usuario
from models.sede import Sede
from models.camara import Camara
from models.auditoria import Auditoria, AuditoriaDetalle
from routes import auth, auditoria, historico, dashboard, usuarios

# Create uploads directory
os.makedirs(os.path.join("static", "uploads"), exist_ok=True)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RANSA - Auditoría de Temperatura", version="1.0.0")

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router)
app.include_router(auditoria.router)
app.include_router(historico.router)
app.include_router(dashboard.router)
app.include_router(usuarios.router)


def seed_data():
    """Insert initial data if database is empty."""
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Usuario).count() > 0:
            return

        print("[SEED] Insertando datos semilla...")

        # Create admin user (password: admin123)
        from routes.auth import get_password_hash
        admin = Usuario(
            username="admin",
            password_hash=get_password_hash("admin123"),
            nombre_completo="Administrador Sistema",
            rol="administrador",
            regional="Nacional"
        )
        db.add(admin)

        # Create auditor user (password: auditor123)
        auditor = Usuario(
            username="jtoscanom",
            password_hash=get_password_hash("auditor123"),
            nombre_completo="Jose Miguel Toscano Molina",
            rol="auditor",
            regional="Costa"
        )
        db.add(auditor)

        auditor2 = Usuario(
            username="jperezs",
            password_hash=get_password_hash("auditor123"),
            nombre_completo="Juan Perez",
            rol="auditor",
            regional="Sierra"
        )
        db.add(auditor2)

        # Create sedes
        sedes_data = [
            ("Galapa", "GAL", "Costa"),
            ("Medellín", "MED", "Antioquia"),
            ("Bogotá", "BOG", "Centro"),
            ("Barranquilla", "BAQ", "Costa"),
            ("Cali", "CAL", "Pacífico"),
        ]
        sedes = []
        for nombre, codigo, regional in sedes_data:
            sede = Sede(nombre=nombre, codigo=codigo, regional=regional)
            db.add(sede)
            sedes.append(sede)

        db.flush()

        # Cámaras específicas por sede
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

        camaras_default = [
            ("Bahia", "Refrigerada"),
            ("Archivos", "Congelada"),
            ("Congelado 1", "Congelada"),
            ("Congelado 2", "Congelada"),
            ("Congelado 3", "Congelada"),
            ("Refrigerado 1", "Refrigerada"),
            ("Refrigerado 2", "Refrigerada"),
            ("Cuarto Frío 1", "Refrigerada"),
        ]

        for sede in sedes:
            camaras_lista = camaras_galapa if sede.codigo == "GAL" else camaras_default
            for nombre, tipo in camaras_lista:
                camara = Camara(nombre=nombre, sede_id=sede.id, tipo=tipo)
                db.add(camara)

        db.commit()
        print("[OK] Datos semilla insertados exitosamente.")
        print("   Usuarios creados:")
        print("      - admin / admin123 (Administrador)")
        print("      - jose.toscano / auditor123 (Auditor)")
        print("      - juan.perez / auditor123 (Auditor)")
    except Exception as e:
        db.rollback()
        print(f"[WARN] Error al insertar datos semilla: {e}")
    finally:
        db.close()


# Run seed on startup
seed_data()


# ============================
# Page Routes (HTML Templates)
# ============================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/auditoria", response_class=HTMLResponse)
async def auditoria_page(request: Request):
    return templates.TemplateResponse("auditoria.html", {"request": request})


@app.get("/historico", response_class=HTMLResponse)
async def historico_page(request: Request):
    return templates.TemplateResponse("historico.html", {"request": request})


@app.get("/historico/detalle/{id}", response_class=HTMLResponse)
async def detalle_auditoria_page(request: Request, id: int):
    return templates.TemplateResponse("detalle_auditoria.html", {"request": request, "auditoria_id": id})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/admin/usuarios", response_class=HTMLResponse)
async def admin_usuarios_page(request: Request):
    return templates.TemplateResponse("admin_usuarios.html", {"request": request})

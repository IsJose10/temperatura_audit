from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.usuario import Usuario
from schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from routes.auth import get_current_user, get_password_hash

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])


def require_admin(current_user: Usuario = Depends(get_current_user)):
    if current_user.rol != "administrador":
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return current_user


@router.get("/", response_model=list[UsuarioResponse])
def get_usuarios(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    query = db.query(Usuario)
    if search:
        query = query.filter(
            (Usuario.username.contains(search)) |
            (Usuario.nombre_completo.contains(search))
        )
    usuarios = query.order_by(Usuario.nombre_completo).all()
    return [UsuarioResponse.model_validate(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(usuario_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UsuarioResponse.model_validate(usuario)


@router.post("/", response_model=UsuarioResponse)
def create_usuario(data: UsuarioCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    existing = db.query(Usuario).filter(Usuario.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    usuario = Usuario(
        username=data.username,
        password_hash=get_password_hash(data.password),
        nombre_completo=data.nombre_completo,
        rol=data.rol,
        regional=data.regional
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return UsuarioResponse.model_validate(usuario)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(usuario_id: int, data: UsuarioUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if data.nombre_completo is not None:
        usuario.nombre_completo = data.nombre_completo
    if data.rol is not None:
        usuario.rol = data.rol
    if data.regional is not None:
        usuario.regional = data.regional
    if data.activo is not None:
        usuario.activo = data.activo

    db.commit()
    db.refresh(usuario)
    return UsuarioResponse.model_validate(usuario)


@router.delete("/{usuario_id}")
def disable_usuario(usuario_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = not usuario.activo
    db.commit()
    return {"message": f"Usuario {'habilitado' if usuario.activo else 'deshabilitado'} exitosamente"}

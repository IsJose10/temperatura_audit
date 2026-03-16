from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UsuarioBase(BaseModel):
    username: str
    nombre_completo: str
    rol: str = "auditor"
    regional: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    rol: Optional[str] = None
    regional: Optional[str] = None
    activo: Optional[bool] = None


class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse

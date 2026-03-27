from pydantic import BaseModel
from typing import Optional


class SedeResponse(BaseModel):
    id: int
    nombre: str
    codigo: str
    regional: Optional[str] = None

    class Config:
        from_attributes = True


class CamaraResponse(BaseModel):
    id: int
    nombre: str
    sede_id: int
    tipo: Optional[str] = None

    class Config:
        from_attributes = True

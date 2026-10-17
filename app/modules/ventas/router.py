from fastapi import APIRouter, BackgroundTasks

from app.core.database import SessionDependency
from app.core.routing import Identifier, Limit, Offset
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaRead

router = APIRouter(prefix="/ventas", tags=["ventas"])


@router.post("/", response_model=VentaRead, status_code=201)
async def crear(datos: VentaCreate, tareas: BackgroundTasks, session: SessionDependency):
    venta = await service.crear(session, datos)
    tareas.add_task(service.notificar_comprobante, venta.id, str(venta.cliente.email))
    return venta


@router.get("/", response_model=list[VentaRead])
async def listar(session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, limit, offset)


@router.get("/{id}", response_model=VentaRead)
async def obtener(id: Identifier, session: SessionDependency):
    return await service.obtener(session, id)

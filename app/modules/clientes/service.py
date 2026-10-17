from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, raiseload

from app.core.service import guardar
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate, PerfilCreate


def consulta_clientes():
    return select(Cliente).options(raiseload("*"), joinedload(Cliente.perfil))


async def obtener(session: AsyncSession, identificador: int) -> Cliente:
    resultado = await session.scalars(
        consulta_clientes()
        .where(Cliente.id == identificador)
        .execution_options(populate_existing=True)
    )
    cliente = resultado.one_or_none()
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente


async def crear(session: AsyncSession, datos: ClienteCreate) -> Cliente:
    cliente = Cliente(**datos.model_dump())
    session.add(cliente)
    await guardar(session, "No se pudo guardar el cliente: el email ya está registrado.")
    return await obtener(session, cliente.id)


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Cliente]:
    resultado = await session.scalars(
        consulta_clientes().order_by(Cliente.id).limit(limit).offset(offset)
    )
    return list(resultado)


async def actualizar(session: AsyncSession, identificador: int, datos: ClienteUpdate) -> Cliente:
    cliente = await obtener(session, identificador)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    await guardar(session, "No se pudo guardar el cliente: el email ya está registrado.")
    return cliente


async def crear_perfil(
    session: AsyncSession, identificador: int, datos: PerfilCreate
) -> PerfilCliente:
    await obtener(session, identificador)
    perfil = PerfilCliente(cliente_id=identificador, **datos.model_dump())
    session.add(perfil)
    await guardar(session, "No se pudo guardar el perfil: el cliente ya tiene uno.")
    return perfil

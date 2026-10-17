from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service import exigir_recurso, guardar
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate


async def crear(session: AsyncSession, datos: EditorialCreate) -> Editorial:
    editorial = Editorial(**datos.model_dump())
    session.add(editorial)
    await guardar(session, "No se pudo guardar la editorial: el nombre ya está registrado.")
    return editorial


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Editorial]:
    resultado = await session.scalars(
        select(Editorial).order_by(Editorial.id).limit(limit).offset(offset)
    )
    return list(resultado)


async def obtener(session: AsyncSession, identificador: int) -> Editorial:
    return await exigir_recurso(session, Editorial, identificador, "Editorial")


async def actualizar(
    session: AsyncSession, identificador: int, datos: EditorialUpdate
) -> Editorial:
    editorial = await obtener(session, identificador)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(editorial, campo, valor)
    await guardar(session, "No se pudo guardar la editorial: el nombre ya está registrado.")
    return editorial

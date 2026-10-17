from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service import exigir_recurso, guardar
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate


async def crear(session: AsyncSession, datos: AutorCreate) -> Autor:
    autor = Autor(**datos.model_dump())
    session.add(autor)
    await guardar(session, "No se pudo guardar el autor.")
    return autor


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Autor]:
    resultado = await session.scalars(select(Autor).order_by(Autor.id).limit(limit).offset(offset))
    return list(resultado)


async def obtener(session: AsyncSession, identificador: int) -> Autor:
    return await exigir_recurso(session, Autor, identificador, "Autor")


async def actualizar(session: AsyncSession, identificador: int, datos: AutorUpdate) -> Autor:
    autor = await obtener(session, identificador)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(autor, campo, valor)
    await guardar(session, "No se pudo guardar el autor.")
    return autor

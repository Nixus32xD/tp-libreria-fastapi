from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service import exigir_recurso, guardar
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate


async def crear(session: AsyncSession, datos: GeneroCreate) -> Genero:
    genero = Genero(**datos.model_dump())
    session.add(genero)
    await guardar(session, "No se pudo guardar el género: el nombre ya está registrado.")
    return genero


async def listar(session: AsyncSession, limit: int, offset: int) -> list[Genero]:
    resultado = await session.scalars(
        select(Genero).order_by(Genero.id).limit(limit).offset(offset)
    )
    return list(resultado)


async def obtener(session: AsyncSession, identificador: int) -> Genero:
    return await exigir_recurso(session, Genero, identificador, "Género")

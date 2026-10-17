from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel


async def guardar(session: AsyncSession, mensaje: str) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=mensaje) from error


async def exigir_recurso(
    session: AsyncSession, modelo: type[SQLModel], identificador: int, nombre: str
) -> SQLModel:
    recurso = await session.get(modelo, identificador)
    if recurso is None:
        raise HTTPException(status_code=404, detail=f"{nombre} no encontrado.")
    return recurso

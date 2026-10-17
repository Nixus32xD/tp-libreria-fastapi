from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Una sesión por petición; su cierre revierte cualquier transacción pendiente."""
    async with request.app.state.session_factory() as session:
        yield session


# Los handlers devuelven DTOs o datos ya precargados; la sesión se libera antes
# de enviar la respuesta y de ejecutar cualquier tarea de segundo plano.
SessionDependency = Annotated[AsyncSession, Depends(get_session, scope="function")]

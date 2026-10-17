from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, raiseload, selectinload

from app.core.service import guardar
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import (
    AutoriaRead,
    LibroCreate,
    LibroDeAutorRead,
    LibroListRead,
    LibroRead,
    LibroUpdate,
)


def consulta_libros(detalle: bool = False):
    consulta = select(Libro).options(
        raiseload("*"), joinedload(Libro.editorial), joinedload(Libro.genero)
    )
    if detalle:
        consulta = consulta.options(selectinload(Libro.autorias).joinedload(LibroAutor.autor))
    return consulta


def resumen(libro: Libro) -> LibroListRead:
    return LibroListRead.model_validate(libro)


def detalle(libro: Libro) -> LibroRead:
    return LibroRead(
        **resumen(libro).model_dump(),
        autores=[
            AutoriaRead.model_validate(autoria)
            for autoria in sorted(libro.autorias, key=lambda item: (item.orden, item.autor_id))
        ],
    )


async def obtener_modelo(session: AsyncSession, identificador: int) -> Libro:
    resultado = await session.scalars(
        consulta_libros(detalle=True)
        .where(Libro.id == identificador)
        .execution_options(populate_existing=True)
    )
    libro = resultado.one_or_none()
    if libro is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado.")
    return libro


async def obtener(session: AsyncSession, identificador: int) -> LibroRead:
    return detalle(await obtener_modelo(session, identificador))


async def crear(session: AsyncSession, datos: LibroCreate) -> LibroRead:
    # Editorial, género y autores se validan con las FK; no se consulta su existencia.
    libro = Libro(**datos.model_dump(exclude={"autores"}))
    libro.autorias = [LibroAutor(**autoria.model_dump()) for autoria in datos.autores]
    session.add(libro)
    await guardar(session, "No se pudo guardar el libro: ISBN repetido o referencias inválidas.")
    return await obtener(session, libro.id)


async def listar(
    session: AsyncSession,
    limit: int,
    offset: int,
    titulo: str | None = None,
    genero_id: int | None = None,
    editorial_id: int | None = None,
) -> list[LibroListRead]:
    consulta = consulta_libros()
    if titulo is not None:
        # SQLAlchemy liga el valor como parámetro, incluso si contiene comillas.
        consulta = consulta.where(Libro.titulo.ilike(f"%{titulo}%"))
    if genero_id is not None:
        consulta = consulta.where(Libro.genero_id == genero_id)
    if editorial_id is not None:
        consulta = consulta.where(Libro.editorial_id == editorial_id)
    resultado = await session.scalars(consulta.order_by(Libro.id).limit(limit).offset(offset))
    return [resumen(libro) for libro in resultado]


async def actualizar(session: AsyncSession, identificador: int, datos: LibroUpdate) -> LibroRead:
    libro = await obtener_modelo(session, identificador)
    for campo, valor in datos.model_dump(exclude_unset=True, exclude={"autores"}).items():
        setattr(libro, campo, valor)
    if "autores" in datos.model_fields_set:
        # Reemplazo atómico; se conservan las asociaciones que siguen presentes.
        existentes = {autoria.autor_id: autoria for autoria in libro.autorias}
        recibidos = {autoria.autor_id for autoria in datos.autores}
        for autor_id, autoria in existentes.items():
            if autor_id not in recibidos:
                await session.delete(autoria)
        for autoria_dto in datos.autores:
            if autoria_dto.autor_id in existentes:
                autoria = existentes[autoria_dto.autor_id]
                autoria.rol, autoria.orden = autoria_dto.rol, autoria_dto.orden
            else:
                session.add(LibroAutor(libro_id=identificador, **autoria_dto.model_dump()))
    await guardar(session, "No se pudo guardar el libro: ISBN repetido o referencias inválidas.")
    return await obtener(session, identificador)


async def listar_por_autor(
    session: AsyncSession, autor_id: int, limit: int, offset: int
) -> list[LibroDeAutorRead]:
    resultado = await session.scalars(
        select(LibroAutor)
        .where(LibroAutor.autor_id == autor_id)
        .options(
            raiseload("*"),
            joinedload(LibroAutor.libro).joinedload(Libro.editorial),
            joinedload(LibroAutor.libro).joinedload(Libro.genero),
        )
        .order_by(LibroAutor.libro_id)
        .limit(limit)
        .offset(offset)
    )
    return [
        LibroDeAutorRead(libro=resumen(autoria.libro), rol=autoria.rol, orden=autoria.orden)
        for autoria in resultado
    ]

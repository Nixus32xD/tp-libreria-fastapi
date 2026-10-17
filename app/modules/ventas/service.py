import asyncio
import logging
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, raiseload, selectinload

from app.core.service import guardar
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import ClienteVentaRead, RenglonRead, VentaCreate, VentaRead

logger = logging.getLogger(__name__)
MAX_TOTAL = Decimal("9999999999.99")


def consulta_ventas():
    return select(Venta).options(
        raiseload("*"),
        joinedload(Venta.cliente),
        selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
    )


def detalle(venta: Venta) -> VentaRead:
    return VentaRead(
        id=venta.id,
        cliente_id=venta.cliente_id,
        fecha=venta.fecha,
        total=venta.total,
        cliente=ClienteVentaRead.model_validate(venta.cliente),
        renglones=[
            RenglonRead(
                libro_id=renglon.libro_id,
                titulo=renglon.libro.titulo,
                cantidad=renglon.cantidad,
                precio_unitario=renglon.precio_unitario,
                subtotal=(renglon.precio_unitario * renglon.cantidad).quantize(Decimal("0.01")),
            )
            for renglon in sorted(venta.renglones, key=lambda item: item.id)
        ],
    )


async def obtener(session: AsyncSession, identificador: int) -> VentaRead:
    resultado = await session.scalars(
        consulta_ventas().where(Venta.id == identificador).execution_options(populate_existing=True)
    )
    venta = resultado.one_or_none()
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada.")
    return detalle(venta)


async def crear(session: AsyncSession, datos: VentaCreate) -> VentaRead:
    # Esta consulta obtiene precios de la base; nunca se aceptan precios del cliente.
    libros = await session.scalars(
        select(Libro)
        .where(Libro.id.in_([renglon.libro_id for renglon in datos.renglones]))
        .options(raiseload("*"))
    )
    por_id = {libro.id: libro for libro in libros}
    if len(por_id) != len(datos.renglones):
        raise HTTPException(status_code=409, detail="La venta contiene un libro inexistente.")
    total = sum(
        (por_id[renglon.libro_id].precio * renglon.cantidad for renglon in datos.renglones),
        start=Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    if total > MAX_TOTAL:
        raise HTTPException(
            status_code=422, detail="El total supera el máximo permitido por venta."
        )
    venta = Venta(cliente_id=datos.cliente_id, total=total)
    # Composición: las partes se crean y se persisten con su venta.
    venta.renglones = [
        RenglonVenta(
            libro_id=renglon.libro_id,
            cantidad=renglon.cantidad,
            precio_unitario=por_id[renglon.libro_id].precio,
        )
        for renglon in datos.renglones
    ]
    session.add(venta)
    await guardar(session, "No se pudo guardar la venta: cliente o libros inválidos.")
    return await obtener(session, venta.id)


async def listar(
    session: AsyncSession, limit: int, offset: int, cliente_id: int | None = None
) -> list[VentaRead]:
    consulta = consulta_ventas()
    if cliente_id is not None:
        consulta = consulta.where(Venta.cliente_id == cliente_id)
    resultado = await session.scalars(consulta.order_by(Venta.id).limit(limit).offset(offset))
    return [detalle(venta) for venta in resultado]


async def notificar_comprobante(venta_id: int, email: str) -> None:
    """Sólo recibe escalares; nunca retiene la sesión de la petición."""
    await asyncio.sleep(0.5)
    logger.info("Comprobante de venta %s enviado a %s (simulado).", venta_id, email)

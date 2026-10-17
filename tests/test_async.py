"""Prueba ASGI real: respuesta antes del aviso y atención concurrente durante sleep."""

import asyncio
import inspect
import logging

import httpx


async def test_notification_after_response_does_not_block_or_keep_session(
    application, catalog, sale_body, caplog
):
    sent = asyncio.Event()
    caplog.set_level(logging.INFO, logger="app.modules.ventas.service")

    async def observed(scope, receive, send):
        async def recording_send(message):
            await send(message)
            if (
                scope["path"] == "/ventas/"
                and message["type"] == "http.response.body"
                and not message.get("more_body", False)
            ):
                sent.set()

        await application(scope, receive, recording_send)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=observed), base_url="http://test"
    ) as http:
        pending = asyncio.create_task(http.post("/ventas/", json=sale_body))
        try:
            await asyncio.wait_for(sent.wait(), timeout=3)
            assert not pending.done(), "El transporte espera la tarea posterior a la respuesta"
            assert application.state.engine.sync_engine.pool.checkedout() == 0, (
                "La sesión debe cerrar antes del aviso"
            )
            assert not any("Comprobante de venta" in record.message for record in caplog.records)
            response = await asyncio.wait_for(http.get("/health/live"), timeout=0.25)
            assert response.status_code == 200
            assert not pending.done(), "El aviso real continúa durante otra petición"
            sale = await asyncio.wait_for(pending, timeout=2)
            assert sale.status_code == 201, sale.text
            assert any(
                "Comprobante de venta" in record.message and "c0@example.com" in record.message
                for record in caplog.records
            )
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)


async def test_all_http_handlers_async(application):
    def routes(router):
        for route in router.routes:
            included = getattr(route, "original_router", None)
            if included is not None:
                yield from routes(included)
            else:
                yield route

    handlers = [
        route.endpoint
        for route in routes(application)
        if getattr(route, "path", "").startswith(
            (
                "/health/",
                "/editoriales/",
                "/generos/",
                "/autores/",
                "/libros/",
                "/clientes/",
                "/ventas/",
            )
        )
    ]
    assert len(handlers) >= 28
    assert all(inspect.iscoroutinefunction(handler) for handler in handlers)

# Evidencia de pruebas y ciclo TDD

Todas las pruebas de integración usan PostgreSQL real. `tests/conftest.py` exige
`TEST_DATABASE_URL` con controlador `postgresql+asyncpg`, base terminada en `_test`
y distinta de `DATABASE_URL`. Aplica `alembic upgrade head` y limpia únicamente esa
base entre pruebas HTTP. No utiliza `create_all`.

Ejecutar desde la raíz:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
```

## TDD Cycle Evidence

| Tarea | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Modelos y relaciones | `tests/test_models.py` | Metadatos SQLModel | Repositorio nuevo | Fallo importando `app` antes de crear modelos | 55/55 iniciales | 59/59 tras ampliar relaciones, restricciones e índices | 59/59; registros `tmp/models-*` |
| Semilla inicial | `tests/test_seed.py` | PostgreSQL/CLI | Modelos verdes | Fallo importando `scripts` antes de crear semilla | 8/8 iniciales | 10/10 al incorporar rollback y errores de puerto/conexión | Registros `tmp/seed-*` |
| Restricciones reales | `tests/test_database.py` | SQL directo/PostgreSQL | Esquema migrado y modelos verdes | Sin RED individual de producción: pruebas de caracterización; se corrigió un error de fixture | 27/27 | Se elude DTO para ejercitar CHECK, UNIQUE y FK; índices en metadatos PostgreSQL | Corrida inicial 26 verdes y un error propio del test corregido |
| Ciclo de vida y salud | `tests/test_lifecycle.py` | HTTP/ASGI | Repositorio nuevo | 2 fallos por ausencia de `app.main` | 2/2 | Liveness sin base y readiness no disponible sin filtrar datos internos | Validado junto con la suite |
| Alta de editorial | `tests/test_api.py::test_crear_editorial` | HTTP/PostgreSQL | Repositorio nuevo, sin API previa | Ejecutado: HTTP 404, esperado 201 | Ejecutado dentro de suite API 53/53 | Alta + nombre duplicado + PATCH parcial + recurso ausente | Ruff aplicado; suite funcional verificada por implementación |
| Contratos, relaciones y transacciones | `tests/test_api.py` | HTTP/PostgreSQL | Primeras 4 pruebas verdes en ejecución incremental | Ampliación ejecutada: `/clientes/no-es-entero` 404, esperado 422 | 53/53 en 17,23 s | C-01 a C-06 y C-08, claves foráneas, rollback, snapshot, decimales, zonas horarias, null, paginación de todos los listados | Organización de fixtures y formato Ruff |
| Consultas constantes C-07 | `tests/test_queries.py` | SQL emitido/PostgreSQL | API 53/53 | Sin RED individual: la implementación con precarga ya existía | 3/3 en primera ejecución | Libro con 1 y 4 autores; venta con 1 y 2 renglones; INSERT sin preconsulta de FK/unicidad | Captura SQL mediante listener removido al finalizar |
| Cierre de sesión antes del aviso | `tests/test_async.py` | ASGI/concurrencia real | C-07 3/3 | Ejecutado: una conexión prestada después del cuerpo HTTP, esperado cero | 2/2 tras `Depends(..., scope="function")` | Respuesta antes del log, petición concurrente durante `asyncio.sleep(0.5)`, cero conexiones prestadas, handlers asincrónicos | Adaptada inspección de routers incluidos de FastAPI 0.143 |
| Offset fuera del rango PostgreSQL | `tests/test_api.py::test_offset_outside_postgresql_bigint_returns_422` | HTTP/PostgreSQL | Suite combinada previa 156/156 | Ejecutado: 2 fallos `asyncpg.DataError`, esperado HTTP 422 | 2/2 tras limitar `offset` al máximo BIGINT en Query | Máximo BIGINT + 1 y un entero de 31 cifras | Restricción central compartida por todos los listados |
| Reemplazo de autorías y género opcional | `tests/test_api.py` | HTTP/PostgreSQL | Suite combinada previa 156/156 | Sin RED individual: cobertura adicional de código existente | 4/4 | Actualiza y elimina autorías, orden de salida, rollback de título y relaciones ante FK inválida; género omitido o null | Sin cambio de producción |

Los modelos, migraciones, semilla y restricciones SQL tienen sus propias pruebas
en `tests/test_models.py`, `tests/test_seed.py` y `tests/test_database.py`.
El resultado combinado final se registra con la validación general de la entrega.

Validación final ejecutada: **162 pruebas aprobadas en 35,97 s** con PostgreSQL real,
incluidas las regresiones de offset y las cuatro pruebas adicionales de autorías y
género opcional. `ruff check .` y `ruff format --check .` también aprobaron. El
registro de la ejecución local queda en `tmp/final-pytest.log` (no versionado).

## Límites del registro TDD

El primer contrato HTTP de catálogo se escribió y ejecutó antes de implementarlo.
La ampliación del archivo de contratos quedó escrita antes de terminar clientes y
ventas; varios casos de catálogo y validación se añadieron cuando su código ya
existía. Por eso esta entrega **no afirma un ciclo RED/GREEN individual para cada
caso**. La prueba C-07 también se añadió sobre consultas ya implementadas. La mejora
de cierre temprano de sesión sí siguió RED/GREEN observado.

La primera inspección de handlers falló porque FastAPI 0.143 incluye routers de
forma diferida; se corrigió la inspección del test recorriendo `original_router`.
Ese fallo era del test y no se presenta como defecto de producción.

## Evidencia funcional

- `test/casos-minimos.http`: C-01 a C-08 con cuerpos y respuestas esperadas.
- `test/crud.http`: contratos de altas, listados, filtros, detalles y PATCH.
- `docs/evidencia-c07.txt`: fragmentos reales SQL copiados desde la captura de la
  prueba C-07. Al volver a ejecutar, la captura nueva queda en
  `tmp/evidencia-c07.txt`, que no se versiona.
- El test asincrónico observa mensajes ASGI reales y usa el `sleep(0.5)` de la
  aplicación; no sustituye la tarea por una función simulada. Comprueba una segunda
  petición mientras el aviso sigue en ejecución. Esto cubre el proceso de prueba,
  sin afirmar pruebas de carga de infraestructura externa.

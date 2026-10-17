# TP Programación III - Librería

API asincrónica de catálogo, clientes y ventas. Resolución de los capítulos 1 a 4:
FastAPI, SQLModel, SQLAlchemy async, PostgreSQL y Alembic.

Para retomar el entorno que ya quedó configurado en esta PC, ver
[entorno local](docs/entorno-local.md). Para un clon nuevo, seguir los pasos siguientes.

## Requisitos

- Python **3.12 o superior** y PostgreSQL **16 o superior**.
- Git. Para ejecutar los archivos `test/*.http`, REST Client de VS Code o una herramienta compatible.
- No se necesitan Redis, autenticación, repositorios ni Unit of Work.

## Levantar desde cero (PowerShell)

```powershell
git clone https://github.com/Nixus32xD/tp-libreria-fastapi.git
cd tp-libreria-fastapi
# Elegir una versión instalada >= 3.12; por ejemplo:
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item env.example .env
```

Crear una base vacía `libreria` en PostgreSQL con un usuario local que tenga permisos
de crear tablas. Editar **solamente el archivo local `.env`** y reemplazar `USUARIO`,
`CLAVE`, host y puerto de `DATABASE_URL`. El controlador debe ser `postgresql+asyncpg`.
Si la contraseña tiene caracteres reservados, codificarlos para URL. `env.example`
contiene marcadores de posición, sin credenciales utilizables.

```powershell
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

- Swagger: <http://127.0.0.1:8000/docs>
- OpenAPI: <http://127.0.0.1:8000/openapi.json>
- Liveness: <http://127.0.0.1:8000/health/live>
- Readiness: <http://127.0.0.1:8000/health/ready>

`GET /health/live` no consulta la base. Readiness ejecuta `SELECT 1`; devuelve 503
con un mensaje propio cuando no puede conectarse. No se crea el esquema al arrancar:
se administra exclusivamente con Alembic.

## Datos de demostración y reinicio

```powershell
python -m scripts.seed
# Reestablecer explícitamente los datos del TP (borra los datos de DATABASE_URL):
python -m scripts.seed --reset --confirm-reset
```

La carga inicial es repetible y deja ids conocidos para `test/*.http`.
El reinicio explícito está pensado para una base **exclusiva de este TP**.
No usarlo sobre otra base ni sobre datos que se quieran conservar.

## Probar

Crear otra base vacía cuyo nombre termine en `_test` (por ejemplo `libreria_test`)
y configurar `TEST_DATABASE_URL` en `.env`. Debe ser distinta de la base de trabajo.
Los tests borran sus datos entre casos y aplican las migraciones; no usan SQLite.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

Para probar manualmente, arrancar el servidor y abrir `test/casos-minimos.http` o
`test/crud.http` con REST Client de VS Code. **Antes de cada archivo**, ejecutar
`python -m scripts.seed --reset --confirm-reset` y luego sus peticiones de arriba
hacia abajo. Los archivos son independientes. Los casos mínimos usan referencias a
respuestas para obtener los ids de ventas: las secuencias de PostgreSQL avanzan
incluso si una inserción termina en rollback. Cada petición indica el resultado
esperado. Los casos C-01 a C-08 también se verifican automáticamente.

## Organización y flujo

```text
app/
  main.py                      # lifespan, aplicación y routers
  core/{config,database}.py     # entorno, fábrica de sesiones y Depends
  modules/
    health/
    editoriales/
    generos/
    autores/
    libros/                    # incluye LibroAutor
    clientes/                  # incluye PerfilCliente
    ventas/                    # incluye RenglonVenta
      models.py                # tablas, constraints y relaciones
      schemas.py               # contratos Create / Update / Read
      service.py               # lógica con sesión explícita
      router.py                # HTTP -> service -> DTO
migrations/                    # Alembic async, dos versiones
scripts/                       # carga inicial y herramientas de evidencia
test/                          # peticiones .http
tests/                         # pruebas automáticas sobre PostgreSQL
docs/                          # evidencia y validación
```

El lifespan crea el motor y la fábrica de sesiones en `app.state` y dispone el motor
al cerrar. `Depends(get_session)` entrega una sesión por petición, con
`expire_on_commit=False`. Los handlers son `async def`; el acceso a PostgreSQL usa
`asyncpg`. Los servicios reciben la sesión como argumento.

## Modelo y decisiones

| Relación | Clave foránea y justificación |
| --- | --- |
| Libro - editorial (agregación) | `libro.editorial_id`: muchos libros comparten una editorial existente. |
| Libro - género (agregación opcional) | `libro.genero_id`, nullable: el género existe antes y puede omitirse. |
| Libro - autor (muchos a muchos con datos) | `libro_autor.libro_id` y `autor_id`, PK compuesta. `rol` y `orden` pertenecen a la autoría. |
| Cliente - perfil (uno a uno) | `perfil_cliente.cliente_id` UNIQUE: como máximo un perfil por cliente; `Cliente.perfil` es escalar. |
| Venta - cliente (asociación) | `venta.cliente_id`: cada venta referencia un cliente existente. |
| Venta - renglón (composición) | `renglon_venta.venta_id`: la parte se crea dentro de `venta.renglones`, con cascada de composición. |
| Renglón - libro (asociación) | `renglon_venta.libro_id`: cada renglón referencia un libro existente. |

Todas las FK tienen índice y navegación en ambos extremos. `libro_autor` es una entidad
de asociación; se navega `libro.autorias[i].autor`. Los `UNIQUE` y `CHECK` se aplican
en PostgreSQL, además de la validación de entrada. Nunca se preconsulta la unicidad.
El alta de libros escribe directamente las FK: una referencia inválida da 409.

- Dinero: `Decimal`, `NUMERIC(10,2)` para precios y `NUMERIC(12,2)` para totales.
  Se serializa como texto decimal, sin errores de punto flotante.
- El servidor lee los precios vigentes, crea los renglones y calcula el total dentro
  de una transacción. No acepta precio, fecha ni total en el alta de venta.
- Las ventas son inmutables: no existen PATCH ni DELETE de ventas ni alta independiente
  de renglones. Cambiar el precio de un libro no altera los precios vendidos.
- La consigna exige stock no negativo, pero no establece descuento ni control de
  disponibilidad al vender. Se conserva esa regla sin agregar un sistema de inventario.
- PATCH modifica únicamente campos enviados; `genero_id: null` quita el género.
  Los demás campos obligatorios no aceptan null. Una lista `autores` enviada en PATCH
  reemplaza la autoría completa de manera atómica.
- Todos los listados, incluidos los anidados, aceptan `limit` (1..100, defecto 20)
  y `offset` (0..9223372036854775807, rango BIGINT de PostgreSQL). Orden estable por id.
- Búsqueda de título sin distinguir mayúsculas y con parámetros ligados.
- Los errores de integridad hacen rollback y responden 409 con mensajes propios;
  nunca se devuelve el SQL ni el nombre de una restricción.
- Las relaciones se declaran con carga perezosa prohibida. Las lecturas usan
  `joinedload` para relaciones a uno y `selectinload` para colecciones.
- La notificación del comprobante es una simulación con `BackgroundTasks`,
  `await asyncio.sleep(0.5)` y log. Recibe datos escalares y no reutiliza la sesión
  de la petición. No se envían correos reales.

## Migraciones

Se entregan dos revisiones generadas con `alembic revision --autogenerate`:

1. Tablas iniciales sin `genero` ni `libro.genero_id`.
2. Tabla `genero`, columna opcional `libro.genero_id`, índice y FK.

Las versiones contienen comentarios de revisión. Para comprobar reversibilidad:

```powershell
alembic current
alembic downgrade -1
alembic upgrade head
alembic check
```

El downgrade elimina el género y su asociación; ejecutarlo sobre una base de prueba.
La aplicación completa requiere `head`.

## Evidencia de consultas (C-07)

Consultar `docs/evidencia-c07.txt`. Los tests cuentan las consultas emitidas por el
motor real al leer detalles con una o varias autorías/renglones. El detalle del libro
y el de venta resuelven cada uno **dos SELECT**, independientemente de la cantidad de
partes. Para observar SQL durante la ejecución, configurar `SQL_ECHO=true` y reiniciar.

La evidencia TDD y los comandos de validación se documentan en `docs/TDD.md`.
GitHub Actions ejecuta la suite sobre PostgreSQL 16.

## Referencias técnicas

- [SQLModel: relaciones muchos a muchos con datos](https://sqlmodel.tiangolo.com/tutorial/many-to-many/link-with-extra-fields/).
- [FastAPI: cierre de dependencias con yield y scope](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).
  Se usa `scope="function"` para liberar la sesión antes de responder y ejecutar el aviso.
  La versión de FastAPI está fijada en requirements y soporta esta opción.

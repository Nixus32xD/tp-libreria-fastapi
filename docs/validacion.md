# Validación de la entrega

## Alcance

Resolución de la consigna de Programación III, unidades 1 a 4: API de librería,
catálogo, clientes y ventas. No requiere interfaz gráfica ni proveedores externos.

| Ejercicio | Implementación y comprobación |
| --- | --- |
| 1. Proyecto y ciclo de vida | Módulos funcionales, configuración por entorno, lifespan, sesión por petición, liveness sin base y readiness con `SELECT 1`. |
| 2. Modelo relacional | Nueve tablas, nombres obligatorios, Decimal, CHECK/UNIQUE/FK, índices y relaciones bidireccionales. Tests de metadata y restricciones en PostgreSQL. |
| 3. Migraciones | Dos revisiones autogeneradas y revisadas. Creación desde vacío, downgrade/reupgrade y `alembic check`. Ver `migraciones.md`. |
| 4. Contratos y CRUD | DTO separados, códigos HTTP, validación, PATCH parcial y listados paginados. |
| 5. Altas relacionadas | Libro con ids y datos de autoría; venta y renglones en una transacción, precios históricos y total del servidor. |
| 6. Sin N+1 | Precarga declarada y carga perezosa prohibida. Dos SELECT por detalle, con uno o varios componentes. Ver `evidencia-c07.txt`. |
| 7. Asincronía | Handlers async y driver asyncpg; aviso simulado con BackgroundTasks y sleep asincrónico, sin reutilizar la sesión HTTP. |

## Entorno local

- Validación realizada el 17/10/2026.
- Python 3.12.14, PostgreSQL 18 (superior al mínimo 16).
- Entorno virtual exclusivo del proyecto y versiones directas fijadas en requirements.
- Cluster y bases exclusivos del TP; los datos de otros proyectos no se utilizan.
- GitHub Actions repite las comprobaciones con Python 3.12 y PostgreSQL 16.

## Resultados locales comprobados

```text
python -m pytest -q
162 passed in 35.97s

python -m ruff check .
All checks passed!

python -m pip check
No broken requirements found.
```

Además de la integración ASGI de pytest, se ejecutaron **48 peticiones HTTP reales**
contra Uvicorn en loopback: 25 del archivo `casos-minimos.http` y 23 de `crud.http`.
Todas coincidieron con los estados esperados. Se comprobaron también los importes,
el precio histórico después de un PATCH y el aviso simulado en el log del servidor.

Tras la prueba manual se restableció y verificó el seed: 4 libros, 2 clientes,
0 ventas, 0 perfiles y Rayuela a `25000.00`. Los `.http` obtienen dinámicamente el
id de cada venta porque los intentos fallidos también avanzan las secuencias.

## Reproducir

```powershell
python -m pip install -r requirements-dev.txt
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic check
python -m scripts.seed
python -m scripts.seed
python -m ruff check .
python -m pytest -q
```

Los comandos de downgrade deben ejecutarse en una base de prueba. La segunda carga
del seed conserva los datos y no duplica registros.

La suite exige `TEST_DATABASE_URL` explícita y una base distinta, terminada en `_test`.
Los tests aplican Alembic y reinician exclusivamente esa base entre casos. No se usa
`create_all` para omitir las migraciones.

## Límites del alcance

- La notificación es un log simulado, tal como pide la consigna.
- Las ventas conservan precios unitarios históricos; el título del libro se lee del
  catálogo vigente, porque la consigna no pide una copia histórica del título.
- No se descuenta stock al vender: se cumple su CHECK no negativo y se mantiene el
  alcance de las reglas de negocio indicadas.
- El repositorio se creó privado. Para una entrega a terceros se debe concederles
  acceso o cambiar su visibilidad desde GitHub.

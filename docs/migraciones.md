# Evidencia de migraciones

Validación realizada el 17 de octubre de 2026 con Python 3.12 y PostgreSQL 18,
en una base local dedicada exclusivamente a revisar las migraciones.
El proyecto requiere PostgreSQL 16 o superior.

## Generación real, en dos etapas

Se creó el entorno mediante `python -m alembic init -t async migrations`.
La configuración carga `DATABASE_URL` desde el entorno o el `.env` no versionado;
importa `app.models` para registrar metadata, sin importar `app.main`.

1. Con los modelos iniciales, **sin** `Genero` ni `Libro.genero_id`:

   ```text
   python -m alembic revision --autogenerate -m "esquema inicial sin generos"
   Detected added table 'autor'
   Detected added table 'cliente'
   Detected added table 'editorial'
   Detected added table 'libro'
   Detected added table 'perfil_cliente'
   Detected added table 'venta'
   Detected added table 'libro_autor'
   Detected added table 'renglon_venta'
   Generating .../1df72eeb127c_esquema_inicial_sin_generos.py ... done
   ```

   Se revisaron CHECK, UNIQUE, PK compuesta, Numeric y zona horaria, además
   de los siete índices de claves foráneas. El índice UNIQUE de
   `perfil_cliente.cliente_id` cumple simultáneamente ambas garantías.
   La plantilla incluye `import sqlmodel` para los `AutoString` autogenerados.
   No se necesitó modificar el DDL de esta primera revisión.
   Después se aplicó `python -m alembic upgrade head`.

2. Se agregaron los modelos y la navegación de género, y se ejecutó:

   ```text
   python -m alembic revision --autogenerate -m "agregar generos y clasificacion opcional"
   Detected added table 'genero'
   Detected added column 'libro.genero_id'
   Detected added index 'ix_libro_genero_id'
   Detected added foreign key (genero_id)(id) on table libro
   Generating .../4b593822f0ea_agregar_generos_y_clasificacion_opcional.py ... done
   ```

   Alembic advirtió que el `drop_constraint()` generado para la FK sin nombre
   fallaría. **Antes de aplicar**, se asignó el nombre
   `fk_libro_genero_id_genero` tanto en upgrade como en downgrade.
   La razón está comentada en la propia migración. La columna permite NULL.

## Ejecución comprobada

Todos los comandos siguientes terminaron correctamente:

```text
python -m alembic upgrade head
  Running upgrade 1df72eeb127c -> 4b593822f0ea
python -m alembic downgrade -1
  Running downgrade 4b593822f0ea -> 1df72eeb127c
python -m alembic upgrade head
  Running upgrade 1df72eeb127c -> 4b593822f0ea
python -m alembic check
  No new upgrade operations detected.
```

También se comprobó la reconstrucción completa sobre la misma base dedicada,
vacía tras el downgrade total:

```text
python -m alembic downgrade base
  Running downgrade 4b593822f0ea -> 1df72eeb127c
  Running downgrade 1df72eeb127c ->
python -m alembic upgrade head
  Running upgrade -> 1df72eeb127c
  Running upgrade 1df72eeb127c -> 4b593822f0ea
```

Las pruebas de metadata y navegación comenzaron con un RED por ausencia de
`app.models`; pasaron luego 55 casos y finalmente 59 tras triangular objetos de
asociación y composición con distintos valores. No se utiliza `create_all`.

Los registros completos de trabajo se guardaron localmente en `tmp/`, excluido
del repositorio. Este documento conserva los comandos y resultados relevantes
sin URLs de conexión, nombres de usuario ni secretos.

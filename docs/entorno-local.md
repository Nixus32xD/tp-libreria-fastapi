# Entorno preparado en esta PC

El checkout está en `F:\TPS\tp-libreria-fastapi`. El repositorio remoto no incluye
el entorno virtual, `.env`, los datos de PostgreSQL ni los logs.

En esta PC se creó una instancia PostgreSQL 18 exclusiva del TP en
`.local\postgres`, escuchando únicamente en `127.0.0.1:55432`. No reemplaza la
configuración ni los datos de otros proyectos. La API de demostración usa la base
`libreria` y la suite usa `libreria_test`.

Después de reiniciar Windows, iniciar esta instancia desde PowerShell:

```powershell
cd F:\TPS\tp-libreria-fastapi
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D "$PWD\.local\postgres" -l "$PWD\.local\postgres.log" start -w
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Swagger queda en <http://127.0.0.1:8010/docs>. El `.env` local ya apunta a esta
instancia; no hace falta copiar `env.example` encima del archivo existente.
El motor se inicializó para datos ficticios locales, sin contraseña y con acceso
de red limitado a loopback.

Para detener la API iniciada en una consola, usar `Ctrl+C`. Para detener únicamente
el PostgreSQL de este TP, con la API ya detenida:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D "$PWD\.local\postgres" stop -m fast -w
```

Para otro equipo o un clon nuevo, seguir el README: instalar PostgreSQL, crear las
bases y configurar un `.env` propio. La carpeta `.local` no se distribuye por Git.

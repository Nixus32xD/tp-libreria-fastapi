import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    sql_echo: bool


def get_settings() -> Settings:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Configurá DATABASE_URL con PostgreSQL y el controlador asyncpg.")
    return Settings(
        database_url=database_url,
        sql_echo=os.getenv("SQL_ECHO", "false").strip().lower() in {"1", "true", "yes"},
    )

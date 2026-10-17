from sqlmodel import SQLModel


class HealthRead(SQLModel):
    estado: str

from sqlmodel import Field, Relationship, SQLModel


class Genero(SQLModel, table=True):
    __tablename__ = "genero"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150, unique=True)

    libros: list["Libro"] = Relationship(  # noqa: F821
        back_populates="genero", sa_relationship_kwargs={"lazy": "raise"}
    )

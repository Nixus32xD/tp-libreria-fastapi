from sqlmodel import Field, Relationship, SQLModel


class Editorial(SQLModel, table=True):
    __tablename__ = "editorial"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150, unique=True)
    pais: str = Field(max_length=100)

    libros: list["Libro"] = Relationship(  # noqa: F821
        back_populates="editorial", sa_relationship_kwargs={"lazy": "raise"}
    )

from sqlmodel import Field, Relationship, SQLModel


class Autor(SQLModel, table=True):
    __tablename__ = "autor"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)
    nacionalidad: str = Field(max_length=100)

    autorias: list["LibroAutor"] = Relationship(  # noqa: F821
        back_populates="autor", sa_relationship_kwargs={"lazy": "raise"}
    )

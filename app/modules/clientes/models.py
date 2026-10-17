from sqlmodel import Field, Relationship, SQLModel


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)
    email: str = Field(max_length=254, unique=True)

    perfil: "PerfilCliente" = Relationship(
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise", "uselist": False}
    )
    ventas: list["Venta"] = Relationship(  # noqa: F821
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise"}
    )


class PerfilCliente(SQLModel, table=True):
    __tablename__ = "perfil_cliente"

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True, unique=True)
    telefono: str = Field(max_length=50)
    direccion: str = Field(max_length=250)

    cliente: "Cliente" = Relationship(
        back_populates="perfil", sa_relationship_kwargs={"lazy": "raise"}
    )

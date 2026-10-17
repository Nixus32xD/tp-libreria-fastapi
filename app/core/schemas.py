from typing import Annotated, ClassVar, Self

from pydantic import ConfigDict, StringConstraints, model_validator
from sqlmodel import Field, SQLModel

MAX_INTEGER = 2_147_483_647
PositiveId = Annotated[int, Field(gt=0, le=MAX_INTEGER)]
Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Pais = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class StrictDTO(SQLModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PartialDTO(StrictDTO):
    """La ausencia conserva el valor; null requiere permiso explícito del contrato."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def validar_nulos_explicitos(self) -> Self:
        for name in self.model_fields_set:
            if getattr(self, name) is None and name not in self.nullable_fields:
                raise ValueError(f"El campo {name} no admite null.")
        return self

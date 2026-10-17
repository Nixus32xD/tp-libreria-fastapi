from typing import Annotated

from fastapi import Path, Query

from app.core.schemas import MAX_INTEGER

Identifier = Annotated[int, Path(gt=0, le=MAX_INTEGER)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=9_223_372_036_854_775_807)]

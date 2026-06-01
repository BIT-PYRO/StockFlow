from typing import Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    results: list[T]


class MessageResponse(BaseModel):
    message: str
    detail: Any = None

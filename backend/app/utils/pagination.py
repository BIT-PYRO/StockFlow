from typing import TypeVar
from sqlalchemy.orm import Query
from app.schemas.common import PaginatedResponse

T = TypeVar("T")


def paginate(query: Query, page: int, page_size: int) -> PaginatedResponse:
    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
    )

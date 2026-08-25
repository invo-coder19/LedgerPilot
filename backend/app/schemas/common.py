"""Common schema utilities and base classes."""

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    """Base schema that enables ORM mode for all response schemas."""
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(ORMBase):
    """Generic paginated list wrapper."""
    total: int
    page: int
    page_size: int
    pages: int
    items: list

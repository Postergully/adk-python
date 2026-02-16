"""Common API response and error models used across P2P services."""

from __future__ import annotations

from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

_T = TypeVar("_T")


class APIError(BaseModel):
  """A normalized error payload for API and tool responses."""

  code: str = Field(min_length=1)
  message: str = Field(min_length=1)
  details: dict[str, Any] | None = None


class APIResponse(BaseModel, Generic[_T]):
  """Single-object response container."""

  success: bool = True
  data: _T | None = None
  error: APIError | None = None

  @model_validator(mode="after")
  def _validate_payload(self) -> APIResponse[_T]:
    if self.success and self.error is not None:
      raise ValueError("A successful response cannot include an error.")
    if not self.success and self.error is None:
      raise ValueError("An unsuccessful response must include an error.")
    return self


class ListResponse(BaseModel, Generic[_T]):
  """List response container with NetSuite-like pagination fields."""

  items: list[_T] = Field(default_factory=list)
  hasMore: bool = False
  totalResults: int | None = Field(default=None, ge=0)

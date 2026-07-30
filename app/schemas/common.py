from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class MetaPayload(BaseModel):
    page: Optional[int] = 1
    limit: Optional[int] = 20
    total: Optional[int] = 0

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    meta: Optional[MetaPayload] = None

    @classmethod
    def ok(cls, data: T, meta: Optional[MetaPayload] = None) -> "StandardResponse[T]":
        return cls(success=True, data=data, error=None, meta=meta)

    @classmethod
    def fail(cls, code: str, message: str, details: Optional[dict[str, Any]] = None) -> "StandardResponse[Any]":
        return cls(
            success=False,
            data=None,
            error=ErrorDetail(code=code, message=message, details=details),
            meta=None
        )

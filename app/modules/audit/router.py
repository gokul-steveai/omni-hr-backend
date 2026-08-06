import uuid
from datetime import date
from typing import Optional

from fastapi import Depends, Query, Request

from app.api.deps import ProtectedAPIRouter, get_audit_service, require_permission
from app.core.services.cache_service import cache_response
from app.models.role import PermissionEnum
from app.models.user import User
from app.modules.audit.schemas import AuditLogRead
from app.modules.audit.service import AuditLogService
from app.schemas.common import MetaPayload, StandardResponse

audit_logs_router = ProtectedAPIRouter()


@audit_logs_router.get(
    "",
    response_model=StandardResponse[list[AuditLogRead]],
    response_model_exclude_none=True,
)
@cache_response(ttl_seconds=60, key_prefix="audit_logs")
async def list_audit_logs(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    module: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_permission(PermissionEnum.AUDIT_READ)),
    audit_service: AuditLogService = Depends(get_audit_service),
):

    logs, total = await audit_service.list_audit_logs(
        page=page,
        limit=limit,
        module=module,
        entity=entity,
        action=action,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    meta = MetaPayload(page=page, limit=limit, total=total)
    return StandardResponse.ok(data=logs, meta=meta)

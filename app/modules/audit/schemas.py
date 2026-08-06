import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    module: str
    action: str
    entity: str
    entity_id: Optional[uuid.UUID] = None
    extra_metadata: Optional[dict] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

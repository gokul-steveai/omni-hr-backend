import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.modules.roles.schemas import RoleWithPermissionsRead


class DepartmentBase(BaseModel):
    id: uuid.UUID
    name: str
    model_config = ConfigDict(from_attributes=True)


class DesignationBase(BaseModel):
    id: uuid.UUID
    title: str
    model_config = ConfigDict(from_attributes=True)


class ProfileResponse(BaseModel):
    id: uuid.UUID
    phone_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    ifsc_swift_code: Optional[str] = None
    joining_date: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    phone_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    ifsc_swift_code: Optional[str] = None
    pan_ssn: Optional[str] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role_id: Optional[uuid.UUID] = None
    role: Optional[RoleWithPermissionsRead] = None
    is_active: bool
    department: Optional[DepartmentBase] = None
    designation: Optional[DesignationBase] = None
    manager_id: Optional[uuid.UUID] = None
    profile: Optional[ProfileResponse] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    designation_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    designation_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None

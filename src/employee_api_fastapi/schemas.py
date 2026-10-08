from datetime import timezone
from typing import (
    Optional, 
    Generic, 
    TypeVar,
    List, 
)
from pydantic import (
    AfterValidator,
    BaseModel, 
    NaiveDatetime,
    EmailStr, 
)
from sqlmodel import Field, SQLModel
from typing_extensions import Annotated


T = TypeVar("T")

Age = Annotated[int, Field(ge=18, le=100)]
Text = Annotated[str, Field(min_length=1, max_length=100)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]

# Stored datetimes are naive UTC; mark them as UTC again on the way out.
UTCDatetime = Annotated[
    NaiveDatetime, AfterValidator(lambda v: v.replace(tzinfo=timezone.utc))
]


# --- Schemas ----------------------------------------------------------------


class EmployeeRequestModel(SQLModel):
    age: Age
    first_name: Text
    last_name: Text
    email: Email
    department: Text


class UpdateModel(SQLModel):
    age: Optional[Age] = None
    first_name: Optional[Text] = None
    last_name: Optional[Text] = None
    email: Optional[Email] = None
    department: Optional[Text] = None


class UpdateManagerModel(SQLModel):
    is_manager: Optional[bool]


class UpdateManagerModel(SQLModel):
    is_manager: bool


class UpdateSalaryModel(SQLModel):
    salary: Annotated[int, Field(ge=0)]


class EmployeeMetadata(BaseModel):
    created_at: UTCDatetime
    updated_at: UTCDatetime


class EmployeeResponseModel(BaseModel):
    """Salary and is_manager are server-controlled, so clients can't set them."""

    id: int
    first_name: str
    last_name: str
    email: str
    age: int
    department: str
    salary: int
    is_manager: bool
    metadata: EmployeeMetadata


class EmployeePage(BaseModel):
    count: int
    total: int
    offset: int
    limit: int
    has_next: bool
    has_previous: bool
    employees: List[EmployeeResponseModel]


class EmployeeBatch(BaseModel):
    count: int
    employees: List[EmployeeResponseModel]


class EmployeeSingle(BaseModel):
    employee: EmployeeResponseModel


class Envelope(BaseModel, Generic[T]):
    data: T


class ApiKeyCreate(SQLModel):
    name: Text
    is_admin: bool = False
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class ApiKeyInfo(BaseModel):
    id: int
    name: str
    prefix: str
    is_admin: bool
    created_at: UTCDatetime
    expires_at: Optional[UTCDatetime]
    revoked_at: Optional[UTCDatetime]


class ApiKeyCreated(BaseModel):
    key: str  # the only time the raw key is ever returned
    api_key: ApiKeyInfo


class ApiKeyList(BaseModel):
    count: int
    keys: List[ApiKeyInfo]

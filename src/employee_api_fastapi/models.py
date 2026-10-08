from typing import Optional

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel

from employee_api_fastapi.db import utcnow


class Employee(SQLModel, table=True):
    __tablename__ = "employees"

    id: int = Field(primary_key=True)
    age: int
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str = Field(max_length=255, unique=True)  # stored lowercase
    department: str = Field(max_length=100)
    salary: int = 80_000
    is_manager: bool = False
    created_at: NaiveDatetime = Field(default_factory=utcnow)
    updated_at: NaiveDatetime = Field(
        default_factory=utcnow,
        sa_column_kwargs={"onupdate": utcnow},
    )



class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    key_hash: str = Field(max_length=64, unique=True, index=True)
    prefix: str = Field(max_length=8)  # for identifying a key in listings
    is_admin: bool = False
    created_at: NaiveDatetime = Field(default_factory=utcnow)
    expires_at: Optional[NaiveDatetime] = None
    revoked_at: Optional[NaiveDatetime] = None

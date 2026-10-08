"""Employee API (FastAPI + SQLModel + SQLite).

Install:
    pip install -U fastapi uvicorn "pydantic[email]" sqlmodel

Run:
    export API_TOKENS="token-one,token-two"
    uvicorn main:app --reload
"""
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, FastAPI, Query, Request
from sqlmodel import func, select
from typing_extensions import Annotated

from employee_api_fastapi.auth import rate_limiter, require_admin, require_api_key
from employee_api_fastapi.db import SessionDep, lifespan
from employee_api_fastapi.helpers import (
    apply_update, get_employee_or_404, paginate, save, to_response,
)
from employee_api_fastapi.models import Employee
from employee_api_fastapi.schemas import (
    EmployeeBatch, EmployeePage, EmployeeRequestModel, EmployeeSingle,
    Envelope, UpdateManagerModel, UpdateModel, UpdateSalaryModel,
)


# --- Routes -----------------------------------------------------------------

app = FastAPI(
    title="Employee API",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
)
router = APIRouter(prefix="/api/v1/employees")


@router.get("")
@rate_limiter(calls=60, seconds=60)
def list_employees(
    request: Request,
    session: SessionDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
) -> Envelope[EmployeePage]:
    query = select(Employee)

    if first_name:
        query = query.where(func.lower(Employee.first_name) == first_name.lower())
    if last_name:
        query = query.where(func.lower(Employee.last_name) == last_name.lower())
    if email:
        query = query.where(Employee.email == email.lower())

    return paginate(session, query, offset, limit)


@router.get("/search")
def search_employees(
    request: Request,
    session: SessionDep,
    q: str = Query(..., min_length=1, max_length=100),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Envelope[EmployeePage]:
    pattern = f"%{q.strip()}%"

    query = select(Employee).where(
        (Employee.first_name.ilike(pattern))
        | (Employee.last_name.ilike(pattern))
        | (Employee.email.ilike(pattern))
        | (Employee.department.ilike(pattern))
    )

    return paginate(session, query, offset, limit)


@router.get("/department/{department}")
def search_department(
    request: Request,
    session: SessionDep,
    department: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Envelope[EmployeePage]:
    query = select(Employee).where(
        Employee.department.ilike(f"%{department.strip()}%")
    )

    return paginate(session, query, offset, limit)


@router.get("/{employee_id}")
@rate_limiter(calls=60, seconds=60)
def get_employee(
    request: Request,
    session: SessionDep,
    employee_id: int,
) -> Envelope[EmployeeSingle]:
    employee = get_employee_or_404(session, employee_id)
    return Envelope(data=EmployeeSingle(employee=to_response(employee)))


@router.post("", status_code=201)
@rate_limiter(calls=60, seconds=60)
def create_employees(
    request: Request,
    session: SessionDep,
    data: Annotated[List[EmployeeRequestModel], Body(min_length=1, max_length=100)],
) -> Envelope[EmployeeBatch]:
    employees = [Employee(**item.model_dump()) for item in data]
    session.add_all(employees)
    save(session, *employees)
    return Envelope(data=EmployeeBatch(
        count=len(employees),
        employees=[to_response(e) for e in employees],
    ))


@router.patch("/{employee_id}")
@rate_limiter(calls=60, seconds=60)
def update_employee(
    request: Request, 
    session: SessionDep, 
    employee_id: int, 
    data: UpdateModel
) -> Envelope[EmployeeSingle]:
    return apply_update(session, employee_id, data.model_dump(exclude_unset=True, exclude_none=True))


@router.put("/{employee_id}/salary", dependencies=[Depends(require_admin)])
@rate_limiter(calls=60, seconds=60)
def set_salary(
    request: Request, 
    session: SessionDep, 
    employee_id: int, 
    data: UpdateSalaryModel
) -> Envelope[EmployeeSingle]:
    return apply_update(session, employee_id, data.model_dump())


@router.put("/{employee_id}/manager", dependencies=[Depends(require_admin)])
@rate_limiter(calls=60, seconds=60)
def set_manager(
    request: Request, 
    session: SessionDep, 
    employee_id: int, 
    data: UpdateManagerModel
) -> Envelope[EmployeeSingle]:
    return apply_update(session, employee_id, data.model_dump())


@router.delete("/{employee_id}", status_code=204)
@rate_limiter(calls=60, seconds=60)
def delete_employee(
    request: Request,
    session: SessionDep,
    employee_id: int,
) -> None:
    employee = get_employee_or_404(session, employee_id)
    session.delete(employee)
    session.commit()


app.include_router(router)
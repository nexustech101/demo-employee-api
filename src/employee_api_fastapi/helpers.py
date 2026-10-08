from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import (
    SQLModel, 
    Session, 
    select, 
    func,
)

from employee_api_fastapi.models import Employee
from employee_api_fastapi.schemas import (
    EmployeeMetadata, EmployeePage, 
    EmployeeResponseModel, EmployeeSingle, 
    Envelope,
)


# --- helpers ---------------------------------------------------------------


def apply_update(session: Session, employee_id: int, changes: dict) -> Envelope[EmployeeSingle]:
    employee = get_employee_or_404(session, employee_id)
    employee.sqlmodel_update(changes)
    save(session, employee)
    return Envelope(data=EmployeeSingle(employee=to_response(employee)))

    
def to_response(e: Employee) -> EmployeeResponseModel:
    return EmployeeResponseModel(
        **e.model_dump(exclude={"created_at", "updated_at"}),
        metadata=EmployeeMetadata(
            created_at=e.created_at, 
            updated_at=e.updated_at
        ),
    )


def paginate(session: Session, query, offset: int, limit: int) -> Envelope[EmployeePage]:
    """`query` must be filtered but not ordered/paginated."""
    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    rows = session.exec(
        query.order_by(Employee.created_at, Employee.id).offset(offset).limit(limit)
    ).all()
    return Envelope(data=EmployeePage(
        count=len(rows),
        total=total,
        offset=offset,
        limit=limit,
        has_next=offset + len(rows) < total,
        has_previous=offset > 0,
        employees=[to_response(e) for e in rows],
    ))
    
    
def get_employee_or_404(session: Session, employee_id: int) -> Employee:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(404, "Employee not found.")
    return employee


def save(session: Session, *employees: Employee) -> None:
    """Commit, turning a duplicate email into a 409."""
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Email already registered.")
    for employee in employees:
        session.refresh(employee)

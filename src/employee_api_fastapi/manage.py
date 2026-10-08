import sys

from sqlmodel import Session, SQLModel

import employee_api_fastapi.models  # noqa: F401  (registers tables for create_all)
from employee_api_fastapi.auth import create_api_key
from employee_api_fastapi.db import engine

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "bootstrap-admin"
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        raw, record = create_api_key(session, name, is_admin=True)
    print(f"id={record.id} key={raw}")

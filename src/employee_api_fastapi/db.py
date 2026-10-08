import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from sqlmodel import Session, SQLModel, create_engine
from typing_extensions import Annotated


load_dotenv()  # must run before DATABASE_URL is read


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///employees.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def utcnow() -> datetime:
    """Naive UTC, because SQLite stores datetimes without timezone info."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

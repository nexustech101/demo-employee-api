from datetime import datetime
import functools
import hashlib
import math
import secrets
import threading
from collections import defaultdict, deque
import time
from typing import Optional
from typing_extensions import Annotated
from fastapi import (
    Depends, HTTPException,
    Request, Security
)
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select

from employee_api_fastapi.db import SessionDep, utcnow
from employee_api_fastapi.models import ApiKey


# --- Rate limiting ----------------------------------------------------------

# TODO: Implement a rate limiter for number of times a route
# can be called in a specific amount time period. Should limit
# requests via cheking the IP address of the request. examples
# would include signing up for an account; obviously we don't
# want users creating multiple accounts (or attempting to).

def rate_limiter(calls: int, seconds: int):
    """Allow `calls` requests per `seconds`, per client, per endpoint.

    The endpoint must be a regular `def` that takes a `request: Request` argument.
    In-memory and per-process: use Redis if you run multiple workers.
    """

    def decorator(func):
        cache = defaultdict(deque)  # client -> timestamps of recent requests
        lock = threading.Lock()  # sync endpoints run in a thread pool

        @functools.wraps(func)
        def wrapper(*args, request: Request, **kwargs):
            client = request.headers.get("X-API-Key") or request.client.host

            with lock:
                times = cache[client]
                now = time.monotonic()

                while times and now - times[0] >= seconds:
                    times.popleft()

                if len(times) >= calls:
                    retry_after = math.ceil(seconds - (now - times[0]))
                    raise HTTPException(
                        429, "Rate limit exceeded.",
                        headers={"Retry-After": str(retry_after)},
                    )

                times.append(now)

            return func(*args, request=request, **kwargs)

        return wrapper

    return decorator


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_api_key(
    session: Session, name: str, is_admin: bool = False,
    expires_at: Optional[datetime] = None,
) -> tuple[str, ApiKey]:
    """Returns (raw_key, record). The raw key is never stored; show it once."""
    raw = "ak_" + secrets.token_urlsafe(32)
    record = ApiKey(
        name=name, key_hash=hash_key(raw), prefix=raw[:8],
        is_admin=is_admin, expires_at=expires_at,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return raw, record


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    session: SessionDep, # type: ignore
    api_key: Optional[str] = Security(api_key_header),
) -> ApiKey:
    # Plain `def`: the DB lookup is sync, so FastAPI runs it in the thread pool.
    if api_key:
        record = session.exec(
            select(ApiKey).where(ApiKey.key_hash == hash_key(api_key))
        ).first()
        if (
            record
            and record.revoked_at is None
            and (record.expires_at is None or record.expires_at > utcnow())
        ):
            return record
    raise HTTPException(401, "Missing or invalid API key.")


def require_admin(key: Annotated[ApiKey, Depends(require_api_key)]) -> ApiKey:
    if not key.is_admin:
        raise HTTPException(403, "Admin key required.")
    return key

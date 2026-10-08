# Employee API

REST API for managing employees. FastAPI + SQLModel, SQLite by default, API-key auth stored in the database.

## Setup

```bash
uv sync                      # or: pip install fastapi uvicorn "pydantic[email]" sqlmodel python-dotenv
```

| Env var        | Default                     | Purpose             |
|----------------|-----------------------------|---------------------|
| `DATABASE_URL` | `sqlite:///employees.db`    | SQLAlchemy DB URL   |

Values can be set in a `.env` file. `sqlite:///employees.db` is a relative path, so run every command from the same directory.

## Run

```bash
uv run python -m employee_api_fastapi.manage "my-admin"   # creates the first admin key, prints it once
uv run uvicorn employee_api_fastapi.app:app --reload --port 8003
```

Tables are created on startup (`create_all`). There are no migrations. Interactive docs are at `/docs`; click **Authorize** and paste a key.

## Project layout

```
src/employee_api_fastapi/
  db.py        engine, get_session, SessionDep, utcnow, lifespan
  models.py    Employee, ApiKey (tables)
  schemas.py   request/response models, Envelope
  helpers.py   to_response, paginate, save, apply_update, get_employee_or_404
  auth.py      rate_limiter, create_api_key, require_api_key, require_admin
  app.py       app + routers
  manage.py    CLI: create an admin key
```

Imports only point down this list (`db` imports nothing local), which avoids circular imports.

## Authentication

Every route requires an `X-API-Key` header.

- Keys look like `ak_<43 url-safe chars>` and are shown once, at creation.
- Only a SHA-256 hash is stored. Lookup is an indexed query on the hash.
- A key is rejected if unknown, revoked (`revoked_at` set), or past `expires_at`.
- `is_admin` keys can call admin routes; others get `403`.

## Endpoints

Base path `/api/v1`. "Admin" means an `is_admin` key is required.

| Method | Path                         | Admin | Description                                    |
|--------|------------------------------|:-----:|------------------------------------------------|
| GET    | `/employees`                 |       | List. Filters: `first_name`, `last_name`, `email` (exact, case-insensitive) |
| GET    | `/employees/search?q=`       |       | Substring match on first name, last name, email, department |
| GET    | `/employees/department/{d}`  |       | Substring match on department                  |
| GET    | `/employees/{id}`            |       | Get one                                        |
| POST   | `/employees`                 |       | Create a batch (1–100), body is a JSON array   |
| PATCH  | `/employees/{id}`            |       | Update `age`, `first_name`, `last_name`, `email`, `department` |
| PUT    | `/employees/{id}/salary`     |   ✓   | Body `{"salary": int >= 0}`                    |
| PUT    | `/employees/{id}/manager`    |   ✓   | Body `{"is_manager": bool}`                    |
| DELETE | `/employees/{id}`            |       | Delete, returns `204`                          |
| POST   | `/keys`                      |   ✓   | Create key. Body `{"name", "is_admin", "expires_in_days"}` |
| GET    | `/keys`                      |   ✓   | List keys (prefix only, never the raw key)     |
| DELETE | `/keys/{id}`                 |   ✓   | Revoke key (soft delete), returns `204`        |

List endpoints take `offset` (default 0) and `limit` (default 50, max 100), ordered by `created_at, id`.

## Validation

- `age`: 18–100
- `first_name`, `last_name`, `department`: 1–100 characters
- `email`: valid address, lowercased, unique
- `salary`: integer >= 0
- New employees default to `salary: 80000`, `is_manager: false`

## Response format

All success bodies are wrapped in `{"data": ...}`.

List / search:

```json
{
  "data": {
    "count": 1, "total": 37, "offset": 0, "limit": 50,
    "has_next": false, "has_previous": false,
    "employees": [
      {
        "id": 1, "first_name": "Michael", "last_name": "Carter",
        "email": "michael.carter@example.com", "age": 34,
        "department": "Engineering", "salary": 80000, "is_manager": false,
        "metadata": {
          "created_at": "2026-10-08T15:00:00Z",
          "updated_at": "2026-10-08T15:00:00Z"
        }
      }
    ]
  }
}
```

Single (`GET`, `PATCH`, `PUT`): `{"data": {"employee": {...}}}`
Batch create: `{"data": {"count": 2, "employees": [...]}}`
Key create: `{"data": {"key": "ak_...", "api_key": {id, name, prefix, is_admin, created_at, expires_at, revoked_at}}}`

## Errors

Errors use FastAPI's default shape, `{"detail": ...}`.

| Status | Cause                                              |
|--------|----------------------------------------------------|
| 401    | Missing, invalid, revoked, or expired key          |
| 403    | Non-admin key on an admin route                    |
| 404    | Employee or key not found                          |
| 409    | Email already registered                           |
| 422    | Request validation failed (`detail` is a list)     |
| 429    | Rate limit exceeded; see the `Retry-After` header  |

## Rate limiting

In-memory sliding window, per API key, per route, per process.

- Employee routes with the decorator (list, get, create, update, salary, manager, delete): 60 requests / 60 s
- `POST /keys`, `DELETE /keys/{id}`: 10 / 60 s
- `GET /keys`: 60 / 60 s
- `/employees/search` and `/employees/department/{d}` are not rate limited

Limits reset on restart and are not shared between workers.

## Example

```bash
KEY=ak_...

# create
curl -X POST localhost:8003/api/v1/employees \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '[{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com","age":36,"department":"Engineering"}]'

# list page 2
curl -H "X-API-Key: $KEY" "localhost:8003/api/v1/employees?offset=50&limit=50"

# issue a non-admin key
curl -X POST localhost:8003/api/v1/keys \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"name":"frontend","is_admin":false,"expires_in_days":90}'
```

On Windows PowerShell, use `curl.exe` and escape the JSON quotes.

## Known limitations

- No tests, no migrations (schema changes need a manual DB reset).
- `/search` does not escape `%` and `_`, so `q=%` matches every row.
- A duplicate email anywhere in a batch fails the whole batch with a generic `409`.
- Failed authentication (`401`) is not rate limited.
- `GET /docs` and `/openapi.json` also require a key, since auth is a global dependency.
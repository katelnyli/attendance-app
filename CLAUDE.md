# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI-based attendance tracking system with Role-Based Access Control (RBAC). Users can upload Excel attendance files, and the system stores attendance records in PostgreSQL. Admin/HR roles can view all attendance data, while regular users can only view their own.

## Tech Stack

- **Backend**: FastAPI (async)
- **Database**: PostgreSQL (Docker container) with asyncpg driver
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Caching**: Redis (with connection pooling)
- **Auth**: JWT tokens with Argon2 password hashing
- **Excel Processing**: pandas + openpyxl

## Development Commands

### Server
```bash
./venv/bin/uvicorn app.main:app --reload
```

### Database Access
```bash
docker exec -it postgres-rbac psql -U postgres -d rbac_db
```

### Database Migrations
```bash
# Create new migration
./venv/bin/alembic revision --autogenerate -m "description"

# Apply migrations
./venv/bin/alembic upgrade head

# Rollback one migration
./venv/bin/alembic downgrade -1
```

## Architecture

### Authentication Flow
1. JWT tokens are created with `{sub: user_id, role: role_name}` payload
2. `get_current_user` dependency extracts token, loads user from DB, and attaches `user.role` from token
3. Role is checked directly via `current_user.role` (not from DB or cache) for optimal performance
4. User details are cached in Redis with key pattern `user:{user_id}:details` (TTL: 600s)
5. Cache is invalidated when user role is updated

### Database Schema

**RBAC Structure** (many-to-many):
- `users` ↔ `user_roles` ↔ `roles` ↔ `role_permissions` ↔ `permissions`
- Each user has one role (admin, hr, or employee)
- Roles have multiple permissions (e.g., `read:attendance`, `read:attendance:self`)

**Attendance Tracking** (one-to-many):
- `users` → `uploaded_files` (tracks who uploaded which Excel file)
- `uploaded_files` → `attendance_records` (stores parsed attendance data)
- `AttendanceRecord` has: `user_name`, `hours_worked`, `date`, `file_id`

### Key Models

**User** (`app/models/user.py`):
- UUID primary key with `uuid_generate_v4()`
- Password hashed with Argon2
- Has `.role` attribute attached from JWT token (not in DB model)

**UploadedFile** (`app/models/uploaded_file.py`):
- Tracks metadata: filename (unique), uploaded_by (user_id), uploaded_at
- One-to-many with AttendanceRecord

**AttendanceRecord** (`app/models/attendance_record.py`):
- Stores individual attendance entries: user_name, hours_worked, date
- Foreign key to UploadedFile
- Multiple records per person (one per day)

### API Endpoints

**Auth** (`/api/v1/auth`):
- `POST /register` - Create new user
- `POST /login` - Returns JWT token
- `GET /me` - Returns cached user details with role

**Attendance** (`/api/v1/attendance`):
- `POST /upload` - Admin/HR only: Upload Excel, parse, store in DB
  - Checks for duplicate filenames
  - Parses columns: `姓名` (name), `打卡时长` (hours), `日期` (date)
  - Sums hours if same person appears multiple times on same date
- `POST /` - Admin/HR only: Query attendance by names from DB
- `POST /export` - Admin/HR only: Export attendance to Excel
- `GET /me` - All users: View own attendance
- `GET /metadata` - Admin/HR only: View all uploaded files metadata

**Users** (`/api/v1/users`):
- `GET /` - Admin only: List all users with roles
- `PUT /{user_id}/role` - Admin only: Update user role (invalidates cache)

### Important Patterns

**Role Checking**:
```python
# Check role from token (fastest - already in memory)
if current_user.role not in ["admin", "hr"]:
    raise HTTPException(status_code=403)
```

**Cache Pattern**:
```python
# Check cache before DB query
cache_key = f"user:{user_id}:details"
cached = await redis_client.get(cache_key)
if cached:
    return json.loads(cached)

# On cache miss, query DB and cache result
await redis_client.setex(cache_key, 600, json.dumps(data))
```

**File Upload & Parsing**:
```python
# Read Excel
contents = await file.read()
df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")

# Create UploadedFile record
uploaded_file = UploadedFile(filename=file.filename, uploaded_by=current_user.id)
db.add(uploaded_file)
await db.flush()  # Get ID before creating child records

# Parse and create AttendanceRecord entries
for _, row in df.iterrows():
    # Check if record exists for same (user, date) in this file
    # If exists: sum hours, else: create new record
```

## Environment Setup

Required `.env` variables:
```
POSTGRES_SERVER=localhost
POSTGRES_USER=admin
POSTGRES_PORT=5432
POSTGRES_PASSWORD=<password>
POSTGRES_DB=attendance_db
SECRET_KEY=<secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Important Notes

- **Always use async/await** - All DB and Redis operations are async
- **Import models in alembic/env.py** - Required for autogenerate to detect changes
- **Excel columns are Chinese** - `姓名` (name), `打卡时长` (hours), `日期` (date)
- **Architecture compatibility** - Use `./venv/bin/` prefix for commands to avoid ARM64/x86_64 conflicts
- **Redis connection pooling** - Use `get_redis()` dependency, never create direct connections
- **Cache invalidation** - Delete cache when user roles are updated

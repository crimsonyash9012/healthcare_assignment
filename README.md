# Healthcare Management API

A production-grade REST API for managing healthcare records, built with Django REST Framework and PostgreSQL. The system handles patient and doctor data, doctor-patient mappings, and user accounts with a strong emphasis on data integrity, auditability, and safe concurrent access.

---

## Engineering Decisions

### Repository / Service Layer Architecture
- Business logic lives in `services.py`; all database queries are isolated in `repositories.py`; views only handle HTTP concerns.
- Separating these layers makes each piece independently testable, keeps ORM details out of business logic, and makes it straightforward to swap the persistence backend without touching service code.

### Optimistic Locking for Concurrent Updates
- Every mutable resource carries an integer `version` field. Update queries filter on both `id` and `version`, then atomically increment `version` using `F('version') + 1`.
- This prevents lost updates when two clients edit the same record at the same time, without holding database-level locks that would reduce throughput.

### Idempotency Key Middleware
- POST endpoints require a client-supplied `Idempotency-Key` header. The key, endpoint, and a SHA-256 hash of the request body are stored; identical replays return the cached response instead of creating a duplicate record.
- Clients can safely retry failed or timed-out requests without risk of creating duplicate patients or doctors.

### JWT Authentication with Token Rotation and Blacklisting
- Short-lived access tokens (15 minutes) are paired with rotating refresh tokens (7 days). Used refresh tokens are immediately blacklisted via `rest_framework_simplejwt.token_blacklist`.
- Limits the exposure window of a stolen token while keeping the user experience smooth through silent refresh flows.

### Custom User Model
- `accounts.User` replaces Django's built-in user model from project inception.
- Avoids a painful migration later and allows first-class additions such as roles, healthcare-specific profile fields, and email-as-username without hacking around the default model.

### Immutable Audit Logging
- Every sensitive read or mutation records the acting user, action type, resource, IP address, and timestamp in a dedicated `audit_logs` table with `auto_now_add` timestamps (never editable).
- Satisfies compliance and traceability requirements (HIPAA-style) and provides a forensic trail for any disputed access.

### Request ID Tracing Middleware
- Each request is assigned a UUID4 `X-Request-ID` (or the client's own header value is reused). The ID is stored in a `ContextVar` and echoed back in the response header.
- Makes it possible to correlate log lines across middleware, services, and repositories for a single request, dramatically reducing debugging time in production.

### OpenAPI Documentation via drf-spectacular
- Schema generation is fully automatic from DRF serializers and `@extend_schema` annotations. Swagger UI and ReDoc are served at `/api/schema/swagger-ui/`.
- Keeps documentation in sync with the actual API contract with zero manual maintenance.

### Tiered Test Suite
- Tests are split into `unit/` (services and repositories with SQLite), `integration/` (full HTTP round-trips), and `concurrency/` (optimistic locking races and concurrent idempotency).
- Each tier can run independently in CI, letting fast unit tests gate every commit while the heavier concurrency tests run on a schedule.

### Environment-Based Configuration
- All secrets and environment-specific values are read through `django-environ`. The `.env` file is git-ignored; sane defaults are provided for local development only.
- Prevents secrets from leaking into version control and makes the same codebase deployable across local, staging, and production without code changes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.1, Django REST Framework |
| Auth | SimpleJWT (rotating tokens + blacklist) |
| Database | PostgreSQL (SQLite for tests) |
| Docs | drf-spectacular (OpenAPI 3) |
| Server | Gunicorn (WSGI) |
| Config | django-environ |

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # then edit with your DB credentials

# Apply migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

## Running Tests

```bash
# All tests
python manage.py test tests

# A specific tier
python manage.py test tests.unit
python manage.py test tests.integration
python manage.py test tests.concurrency
```

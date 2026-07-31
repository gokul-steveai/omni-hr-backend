# Backend Architecture: OmniHR API

FastAPI backend application utilizing Async SQLAlchemy 2.0, Pydantic v2, and `uv` package management.

---

## 1. Modular Directory Structure

```
backend/
├── app/
│   ├── modules/                        # Feature-Driven Domain Modules (auth, users, leaves, payroll)
│   │   ├── auth/                       # Router, AuthService, Schemas
│   │   └── users/                      # Router, UserService, UserRepository, Schemas
│   ├── db/                             # Engine, SessionMaker, UnitOfWork
│   ├── core/                           # Config, PasswordService, TokenService
│   ├── repositories/                   # BaseRepository[ModelType]
│   └── models/                         # SQLAlchemy 2.0 ORM Entity Blueprints
├── scripts/                            # Verification & DB Seed Scripts
└── pyproject.toml                      # `uv` Dependency & Project Configuration
```

---

## 2. Architectural Patterns

* **Unit of Work (UOW)**: Transaction management is encapsulated inside `async with UnitOfWork(database_session) as unit_of_work:` context managers.
* **Repository Pattern**: Data access is isolated within `BaseRepository[ModelType]` and domain repositories.
* **Service-Repository Decoupling**: API routers delegate 100% of business logic to domain services.
* **Dynamic RBAC & Fine-Grained Permissions**:
  - Roles and permissions are stored dynamically in relational tables (`roles`, `permissions`, `role_permissions`).
  - New permissions are registered via seed scripts or `POST /api/v1/permissions` API endpoints without requiring DDL database schema migrations.
  - Endpoints enforce authorization via `@require_permission("code")` or `@require_roles([...])` dependencies.
* **Role-Bounded Security**: Public registration strictly assigns default `EMPLOYEE` system role. Elevated or custom roles are provisioned by Admins.

---

## 3. Environment Execution (`uv`)

```bash
# Sync dependencies
uv sync

# Seed test database accounts
uv run python scripts/seed_db.py

# Execute verification suite
uv run python scripts/verify_module1.py

# Launch FastAPI development server
uv run uvicorn app.main:app --reload --port 8000
```

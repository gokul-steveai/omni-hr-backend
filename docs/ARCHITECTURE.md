# Backend Architecture: OmniHR API

FastAPI backend application utilizing Async SQLAlchemy 2.0, Pydantic v2, and `uv` package management.

---

## 1. Modular Directory Structure

```
backend/
├── app/
│   ├── modules/                        # Feature-Driven Domain Modules (auth, users, leaves, payroll)
│   │   ├── auth/                       # Public & Protected Routers, AuthService, Schemas
│   │   └── users/                      # ProtectedAPIRouter, UserService, UserRepository, Schemas
│   ├── db/                             # Engine, SessionMaker
│   ├── api/                            # Common Dependencies & ProtectedAPIRouter (deps.py)
│   ├── core/                           # Config, PasswordService, TokenService
│   ├── repositories/                   # BaseRepository[ModelType]
│   └── models/                         # SQLAlchemy 2.0 ORM Entity Blueprints (PermissionEnum)
├── scripts/                            # Verification & DB Seed Scripts
└── pyproject.toml                      # `uv` Dependency & Project Configuration
```

---

## 2. Architectural Patterns

* **Type-Safe RBAC & PermissionEnum**: All fine-grained permission codes are defined in `PermissionEnum(str, Enum)` in `app.models.role`. Endpoints enforce permissions via `current_user: User = Depends(require_permission(PermissionEnum.USERS_READ))`.
* **ProtectedAPIRouter & Router-Level Auth**: Protected modules instantiate `ProtectedAPIRouter`, enforcing `Depends(get_current_user)` authentication across all endpoints automatically. Unauthenticated endpoints (`/login`, `/refresh`) mount on `public_auth_router`.
* **Constructor Dependency Injection**: Services receive repository dependencies via constructors. API endpoints inject services directly via `Depends(get_*_service)`.
* **Repository Pattern**: Data access is isolated within `BaseRepository[ModelType]` and domain repositories.
* **Service-Repository Decoupling**: API routers delegate 100% of business logic to domain services.

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

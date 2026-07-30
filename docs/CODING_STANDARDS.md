# Backend Engineering Standards

Coding standards, architecture principles, and software design patterns for the OmniHR FastAPI backend.

---

## 1. Core Principles & Discipline

### 1.1 SOLID Principles
* **SRP**: API endpoints handle HTTP routing; Services encapsulate business logic; Repositories manage database access.
* **OCP**: Extend system capabilities (leave approval strategies, tax calculation engines, AI tools) via abstract interfaces and registry decorators without modifying existing core code.
* **LSP**: Domain repositories inherit consistently from generic `BaseRepository[ModelType]`.
* **ISP**: Pydantic v2 request/response schemas expose strictly required properties per endpoint.
* **DIP**: Utilize FastAPI `Depends` for dependency injection of database sessions, security contexts, and business services.

### 1.2 DRY & YAGNI
* Eliminate duplicated business rules, DB query patterns, and API payload definitions.
* Avoid speculative over-engineering; build clean, pragmatic code for active requirements.

### 1.3 Feature-Driven Modular Architecture
* Group code into feature modules under `backend/app/modules/{auth, users, leaves, payroll, timesheets, attendance, ai_agent}` containing dedicated `router.py`, `service.py`, `repository.py`, and `schemas.py`.

### 1.4 Unit of Work Pattern
* Manage multi-repository operations inside `UnitOfWork(database_session)` context managers (`async with UnitOfWork(db) as unit_of_work:`).
* Services must never invoke raw `db.commit()` or `db.rollback()` directly.

### 1.5 Expressive Naming Standard
* Use self-descriptive names for variables, parameters, classes, and functions (`user_entity`, `database_session`, `unit_of_work`, `persisted_token`). Cryptic single-letter or abbreviated names are strictly forbidden.

---

## 2. Technology Stack

* **Framework**: FastAPI (Python 3.12+), SQLAlchemy 2.0 (Async), Pydantic v2.
* **Package Manager**: `uv` (`pyproject.toml`).
* **Database**: Async PostgreSQL with `asyncpg` driver (SQLite `aiosqlite` for local dev).
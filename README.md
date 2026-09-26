# Inventory & Order Management System

> A small-business billing and stock-control web application — _"Inventory Mama"_.
> Track products and stock levels, record sales as orders, generate invoices,
> accept full or partial payments, and get alerted before you run out of stock.

Built as a complete, commercial-grade end-user application:

| Layer | Technology |
| --- | --- |
| API | **FastAPI** (Python 3.12), SQLAlchemy 2.0 ORM, Pydantic v2 |
| Database | **PostgreSQL 16** (production) / **SQLite** (zero-config dev & tests) |
| Auth | JWT bearer tokens (PyJWT, HS256) + PBKDF2-SHA256 password hashing |
| Frontend | **React 18 + TypeScript + Vite**, React Router, Context API |
| Testing | **pytest** (unit + integration, FastAPI `TestClient`) & Vitest |
| Shipping | **Docker** + **docker-compose**, **GitHub Actions** CI |

---

## Table of contents

1. [Features](#features)
2. [Screens](#screens)
3. [Architecture](#architecture)
4. [Getting started (Docker)](#getting-started-docker)
5. [Getting started (local dev)](#getting-started-local-dev)
6. [Demo data & credentials](#demo-data--credentials)
7. [API documentation](#api-documentation)
8. [Testing](#testing)
9. [Configuration reference](#configuration-reference)
10. [Maintenance guide](#maintenance-guide)
11. [User stories & personas](#user-stories--personas)
12. [Project plan & cost estimate](#project-plan--cost-estimate)
13. [Requirements coverage (JD mapping)](#requirements-coverage-jd-mapping)
14. [Project layout](#project-layout)

---

## Features

- **Product catalogue** — SKU, name, category, selling/cost price, unit price,
  stock-in-hand and a per-product low-stock threshold. Soft-delete keeps
  historical orders and invoices intact.
- **Stock control with a full audit trail** — every change is written to
  `stock_movements` (purchase / sale / return / adjustment) recording the delta,
  the resulting quantity and an optional reference & note.
- **Orders** — create as a *draft* and confirm later, or confirm immediately.
  Duplicate order lines are merged, and stock is validated **atomically** before
  any deduction so a partially-fulfilled order can never be left behind.
- **Cancellation & returns** — cancelling a confirmed order restocks the items
  and cancels the linked invoice.
- **Invoicing** — confirming an order auto-generates a numbered invoice
  (`INV-YYYY-NNNNNN`). Invoice status is *derived*: `unpaid`, `partially_paid`,
  `paid`, `cancelled`.
- **Payments** — record full or partial payments via Cash / Card / UPI / Bank
  transfer. Overpayment is rejected with a clear error.
- **Low-stock alerts** — a dedicated view lists every item at or below its
  threshold together with the deficit and a one-click restock action.
- **Dashboard** — revenue, outstanding balance, inventory value, product/order
  counts and a "needs restocking" preview.
- **Authentication & roles** — the first registered account becomes the **owner**;
  the `/api/auth/token` endpoint issues a JWT used for all protected routes.

---

## Screens

| Screen | Route | Purpose |
| --- | --- | --- |
| Login / Register | `/login` | Sign in or create the owner account |
| Dashboard | `/` | KPIs + low-stock preview |
| Inventory | `/inventory` | Product CRUD, search, stock adjustment |
| Billing | `/billing` | Point-of-sale style checkout |
| Orders | `/orders` | Order history, confirm/cancel, payments |
| Low-stock alerts | `/alerts` | Items to reorder + restock |

---

## Architecture

```
┌─────────────────────┐        ┌───────────────────────────────┐        ┌────────────────┐
│  React + TypeScript │  /api  │  FastAPI (routers → crud)      │  ORM   │  PostgreSQL    │
│  (Vite dev / nginx) │ ─────► │  auth · products · orders ·    │ ─────► │  (SQLite in    │
│  Context (auth)     │ ◄───── │  invoices · alerts             │ ◄───── │   dev/tests)   │
└─────────────────────┘  JSON  └───────────────────────────────┘        └────────────────┘
```

The backend is layered deliberately:

- `app/routers/*` — thin HTTP layer: validation, status codes, dependencies.
- `app/crud/*` — all business rules (stock maths, invoicing, payments, reports).
  Domain errors (`OrderError`, `BillingError`) are raised here and translated to
  HTTP responses by the routers.
- `app/models.py` — SQLAlchemy models; money columns use `Numeric(12, 2)` and
  arithmetic is done with `Decimal` quantised to 2 places to avoid float drift.

---

## Getting started (Docker)

The fastest path — launches PostgreSQL, the API and the nginx-served frontend.

```bash
# from the repository root
cp .env.example .env        # optional: edit secrets
docker compose up --build
```

| Service | URL |
| --- | --- |
| Web app | <http://localhost:8080> |
| API | <http://localhost:8000> |
| Swagger UI | <http://localhost:8000/docs> |
| ReDoc | <http://localhost:8000/redoc> |

Seed demo data inside the running backend container:

```bash
docker compose exec backend python -m app.seed
```

---

## Getting started (local dev)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # defaults to SQLite — no DB server needed

python -m app.seed                 # optional demo data
uvicorn app.main:app --reload      # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173  (proxies /api → :8000)
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so the frontend
uses relative URLs in every environment. Override with `VITE_API_TARGET` if your
API runs elsewhere.

---

## Demo data & credentials

Running `python -m app.seed` creates:

- **Owner account:** `owner` / `owner123`
- 7 pharmacy / stationery / beverage products — several deliberately below their
  threshold so the alerts view has content.
- One **confirmed** order with stock deducted, an invoice and a partial UPI
  payment (status `partially_paid`).
- One **draft** order ready for you to confirm in the UI.

> ⚠️ Change the demo password and `SECRET_KEY` before any real deployment.

---

## API documentation

Interactive, always up-to-date documentation is generated automatically by
FastAPI from the Pydantic schemas:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

### Endpoint summary

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Create a user (first user becomes owner) |
| `POST` | `/api/auth/token` | OAuth2 password login → JWT |
| `GET` | `/api/auth/me` | Current user profile |
| `GET` | `/api/products` | List/search products (`search`, `low_stock_only`) |
| `POST` | `/api/products` | Create a product |
| `GET` | `/api/products/{id}` | Retrieve a product |
| `PATCH` | `/api/products/{id}` | Update a product |
| `DELETE` | `/api/products/{id}` | Soft-delete a product |
| `POST` | `/api/products/{id}/stock` | Adjust stock (+/-) with a reason |
| `GET` | `/api/products/{id}/movements` | Stock movement history |
| `GET` | `/api/orders` | List orders (filter by status) |
| `POST` | `/api/orders` | Create/confirm an order |
| `GET` | `/api/orders/{id}` | Retrieve an order |
| `POST` | `/api/orders/{id}/confirm` | Confirm a draft order |
| `POST` | `/api/orders/{id}/cancel` | Cancel (and restock) an order |
| `GET` | `/api/invoices` | List invoices |
| `GET` | `/api/invoices/{id}` | Retrieve an invoice |
| `POST` | `/api/invoices/{id}/payments` | Record a (partial) payment |
| `GET` | `/api/alerts` | Low-stock alerts |
| `GET` | `/api/reports/summary` | Dashboard KPIs |
| `GET` | `/api/health` | Liveness probe |

Authenticate by calling `/api/auth/token` with form fields `username` &
`password`, then send `Authorization: Bearer <token>`.

---

## Testing

### Backend

```bash
cd backend
pytest                                   # run the suite
pytest --cov=app --cov-report=term-missing   # with coverage
ruff check app tests                     # lint
```

Tests run against an **in-memory SQLite** database (`StaticPool`) with FastAPI
dependency overrides, so they need no external services and are fully isolated.

Coverage includes:

- stock movements & the low-stock flag
- guard against negative stock
- product soft-delete
- draft vs. confirmed orders
- duplicate order-line merging
- insufficient-stock rejection (atomic validation)
- order cancellation & restocking
- partial payments, status derivation and overpayment rejection
- an end-to-end API flow (register → login → product → order → invoice → payment)
- duplicate SKU rejection

### Frontend

```bash
cd frontend
npm test          # vitest (single run)
npm run typecheck # tsc --noEmit
npm run lint      # eslint
npm run build     # production bundle
```

---

## Configuration reference

Backend settings are read from environment variables (or `backend/.env`):

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./inventory.db` | SQLAlchemy URL. Use `postgresql+psycopg://…` for Postgres |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **must** be changed in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Token lifetime |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `LOW_STOCK_THRESHOLD_DEFAULT` | `10` | Default threshold for new products |
| `CURRENCY` | `INR` | Display currency |
| `TAX_RATE` | `0.0` | Reserved for tax calculations |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000,http://localhost:8080` | Comma-separated allowed origins |
| `ENVIRONMENT` | `development` | Free-form environment label |
| `DEBUG` | `true` | Debug flag |

Root-level `docker-compose.yml` additionally reads `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY`, `ENVIRONMENT`, `DEBUG` and
`CORS_ORIGINS` from a root `.env` file.

---

## Maintenance guide

**Day-to-day**

- Low-stock items appear automatically on the Alerts page and the dashboard.
- Cancel an order (not the invoice) to return items to stock — the invoice is
  cancelled in the same transaction.
- Products are **soft-deleted** (`is_active = false`) so past orders/invoices
  keep their names and prices. Re-activate by updating `is_active`.

**Schema changes**

- Tables are created automatically on startup (`init_db`) which suits this
  project's scope. For evolving a live database, introduce
  [Alembic](https://alembic.sqlalchemy.org/) migrations:
  `alembic init migrations` → autogenerate → `alembic upgrade head`.

**Backups** — for PostgreSQL, `pg_dump` the `db` volume and store the dump off
the host. For SQLite, copy `inventory.db` (safe when the app is stopped).

**Logs** — the API logs to stdout (`logging`). `docker compose logs -f backend`
streams them; ship to your platform's log sink in production.

**Dependencies**

- Backend pins live in [`backend/requirements.txt`](backend/requirements.txt)
  and [`backend/requirements-dev.txt`](backend/requirements-dev.txt).
- Frontend pins live in [`frontend/package.json`](frontend/package.json).
- CI (`.github/workflows/ci.yml`) runs lint, tests and a Docker build on every
  push/PR.

**Security checklist before go-live**

1. Set a strong, unique `SECRET_KEY`.
2. Restrict `CORS_ORIGINS` to your real domain(s).
3. Serve over HTTPS (terminate TLS at nginx or your load balancer).
4. Replace the demo owner account / password.

---

## User stories & personas

**Persona — "Meena", pharmacy owner.** Runs a small neighbourhood pharmacy with
one part-time helper. She needs to know what's running low and to bill customers
quickly, without training on accounting software.

| # | As a… | I want to… | So that… |
| --- | --- | --- | --- |
| 1 | owner | add products with a reorder threshold | the system warns me before I run out |
| 2 | owner | see low-stock items on a dashboard | I can reorder in one trip |
| 3 | cashier | build a bill by tapping products | checkout is fast at a busy counter |
| 4 | cashier | take a partial payment | regulars can pay the rest later |
| 5 | owner | see which invoices are unpaid | I can follow up on dues |
| 6 | owner | cancel a mistaken order and restock it | my stock count stays correct |
| 7 | owner | see a movement history per product | I can investigate stock discrepancies |
| 8 | owner | have a running record of revenue | I know how the shop is doing |

---

## Project plan & cost estimate

Three milestones over a four-week schedule:

| Milestone | Scope | Duration |
| --- | --- | --- |
| **M1 — Foundation** | Repo scaffolding, data model, auth, product & stock CRUD, core tests | Week 1 |
| **M2 — Transactions** | Orders, invoicing, payments, low-stock alerts, integration tests | Weeks 2–3 |
| **M3 — Polish & ship** | React dashboard, Docker images, CI, documentation, UAT | Week 4 |

**Effort & cost estimate** (indicative, small-business scale):

| Role | Effort | Rate (INR/hr) | Cost (INR) |
| --- | --- | --- | --- |
| Design & analysis | 16 h | 900 | 14,400 |
| Backend development | 60 h | 1,000 | 60,000 |
| Frontend development | 50 h | 1,000 | 50,000 |
| Testing & debugging | 24 h | 900 | 21,600 |
| Documentation & deployment | 14 h | 900 | 12,600 |
| **Total** | **164 h** | — | **≈ 1,58,600** |

Recurring running costs: PostgreSQL managed instance and a small container host
(≈ ₹1,500–₹3,500 / month depending on provider), plus a domain name.

---

## Requirements coverage (JD mapping)

| Required competency | Where it is demonstrated |
| --- | --- |
| Analysis & design | Layered architecture, normalised schema with audit trail, this README & OpenAPI contract |
| Programming | FastAPI + SQLAlchemy + React/TypeScript across the stack |
| Debugging & modification | Edge cases handled: duplicate line merging, atomic stock validation, returns/restock, partial payments, overpayment guard, float-safe `Decimal` money |
| Testing & troubleshooting | pytest unit + integration suite (isolated in-memory DB) and CI that fails on lint/test/build errors |
| Documentation | This README (setup / install / maintenance), docstrings throughout, auto-generated Swagger & ReDoc |
| Interfacing with users | Persona-driven user stories (see above) and a low-friction point-of-sale UI |
| Cost estimates & schedules | Milestone plan and effort/cost table (see above) |
| Commercial application | A deployable, containerised product solving a real small-business problem |

---

## Project layout

```
Inventory_mama/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, lifespan, /api/health
│   │   ├── config.py          # pydantic-settings configuration
│   │   ├── database.py        # engine, session, Base, init_db
│   │   ├── models.py          # SQLAlchemy models & enums
│   │   ├── schemas.py         # Pydantic request/response DTOs
│   │   ├── security.py        # password hashing + JWT
│   │   ├── dependencies.py    # get_current_user, require_owner
│   │   ├── seed.py            # demo data
│   │   ├── crud/              # business logic (products, orders, billing, reports)
│   │   └── routers/           # auth, products, orders, invoices, alerts
│   ├── tests/                 # pytest unit + integration tests
│   ├── requirements*.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api.ts             # typed fetch client
│   │   ├── types.ts           # shared API types
│   │   ├── context/           # AuthContext
│   │   ├── components/        # Layout, Modal, StatCard
│   │   ├── pages/             # Login, Dashboard, Inventory, Billing, Orders, Alerts
│   │   ├── utils/format.ts     # currency / date formatting
│   │   └── styles.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── nginx.conf
│   └── Dockerfile
├── .github/workflows/ci.yml   # lint · test · build
├── docker-compose.yml         # db + backend + frontend
├── .env.example
└── README.md
```

---

_Built with FastAPI, React and PostgreSQL. Licensed for the shop owner who commissioned it._

# StockFlow

A full-stack Inventory & Order Management System built with FastAPI, React, and PostgreSQL.

## Features

- **Dashboard** — live KPIs (products, customers, orders, revenue, pending orders, low-stock alerts) with recent activity, order status breakdown, and low-stock alerts
- **Products** — full CRUD with search, category/status filters, pagination, and restock support
- **Customers** — full CRUD with client-side search (name, email, phone) and avatar initials
- **Orders** — master-detail layout; create orders with multi-line items, advance order lifecycle (pending → confirmed → completed / cancelled), delete
- **Inventory Transactions** — immutable stock-movement ledger with product, type (IN / OUT / ADJUSTMENT), and date-range filters; page-number pagination
- **Docker** — production-ready multi-service compose: nginx-served SPA proxies `/api/` to FastAPI; PostgreSQL with health-checks and a persistent volume

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router v6, Axios, CSS Modules, Vite 5 |
| Backend | FastAPI 0.136, SQLAlchemy 2.0 (ORM), Pydantic v2, Uvicorn |
| Database | PostgreSQL 16 |
| Serving | nginx 1.27 (static SPA + reverse proxy) |
| Containers | Docker, Docker Compose |

---

## Project Structure

```
inventory-management-system/
├── backend/
│   ├── app/
│   │   ├── config.py          # Pydantic-settings configuration
│   │   ├── crud.py            # All database operations
│   │   ├── database.py        # SQLAlchemy engine + session
│   │   ├── main.py            # FastAPI app, CORS, lifespan
│   │   ├── models.py          # ORM models (Product, Customer, Order, …)
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   └── routes/            # One router per resource
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # Shared UI components (DataTable, FormModal, …)
│   │   ├── pages/             # Dashboard, Products, Customers, Orders, Transactions
│   │   ├── services/          # Axios service modules per resource
│   │   ├── layouts/           # MainLayout (sidebar + navbar)
│   │   └── styles/            # globals.css with design tokens
│   ├── Dockerfile             # Multi-stage: node build → nginx serve
│   ├── nginx.conf
│   └── vite.config.js
├── docker-compose.yml         # Full-stack production compose
├── .env.example
└── README.md
```

---

## Local Development Setup

### Prerequisites

- **Python 3.11+** and **Node.js 20.x**
- **PostgreSQL 16** running locally, **or** Docker Desktop for the containerised database

### 1 — Start PostgreSQL

```bash
# Option A: Docker (recommended)
docker compose -f docker-compose.postgres.yml up -d

# Option B: local PostgreSQL — create the database manually
createdb inventory_db
```

### 2 — Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env      # then set DATABASE_URL in .env
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/inventory_db

# Run the development server
$env:PYTHONPATH = 'path/to/backend'   # Windows PowerShell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000`  
Interactive API docs: `http://localhost:8000/docs`

### 3 — Frontend

```bash
cd frontend

npm install

# Start the Vite dev server (proxies /api/* to localhost:8000)
npx vite --host --force
```

Frontend available at: `http://localhost:5173`

---

## Docker (Production)

All three services are wired together in the root `docker-compose.yml`.

```bash
# 1. Copy and configure environment variables
cp .env.example .env

# 2. Build and start all services
docker compose up --build

# 3. Subsequent starts (no rebuild needed)
docker compose up -d

# 4. Stop and remove containers (keeps the database volume)
docker compose down

# 5. Stop and wipe everything including the database volume
docker compose down -v
```

The app is served at `http://localhost` (port 80 by default; change `APP_PORT` in `.env`).

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password — **change in production** |
| `POSTGRES_DB` | `inventory_db` | Database name |
| `POSTGRES_PORT` | `5432` | Host port for the database |
| `CORS_ORIGINS` | `http://localhost,http://localhost:80` | Comma-separated allowed origins |
| `UVICORN_WORKERS` | `2` | Number of backend worker processes |
| `APP_PORT` | `80` | Host port for the nginx frontend |

### Architecture

```
Browser
  └─► nginx :80
        ├─ /api/*  ──proxy_pass──► backend:8000  (prefix stripped)
        └─ /*      ──try_files──► React SPA (index.html)

backend:8000  ──SQLAlchemy──► db:5432 (PostgreSQL)
```

---

## API Overview

Interactive documentation is available at `/docs` (Swagger UI) and `/redoc`.

### Products — `/products`

| Method | Path | Description |
|---|---|---|
| `GET` | `/products` | List products; filters: `search`, `category`, `status`, `min_price`, `max_price` |
| `POST` | `/products` | Create a product |
| `GET` | `/products/{id}` | Get a single product |
| `PUT` | `/products/{id}` | Update a product |
| `DELETE` | `/products/{id}` | Delete a product |
| `POST` | `/products/{id}/restock` | Add stock (creates an IN transaction) |

### Customers — `/customers`

| Method | Path | Description |
|---|---|---|
| `GET` | `/customers` | List customers (`skip`, `limit`) |
| `POST` | `/customers` | Create a customer |
| `GET` | `/customers/{id}` | Get a single customer |
| `PUT` | `/customers/{id}` | Update a customer |
| `DELETE` | `/customers/{id}` | Delete a customer |

### Orders — `/orders`

| Method | Path | Description |
|---|---|---|
| `GET` | `/orders` | List orders (`skip`, `limit`) |
| `POST` | `/orders` | Create an order with line items |
| `GET` | `/orders/{id}` | Get order + items |
| `PATCH` | `/orders/{id}/status` | Advance order status |
| `DELETE` | `/orders/{id}` | Delete an order |

### Inventory Transactions — `/inventory-transactions`

| Method | Path | Description |
|---|---|---|
| `GET` | `/inventory-transactions` | Paginated ledger; filters: `product_id`, `transaction_type`, `start_date`, `end_date` |

### Dashboard — `/dashboard`

| Method | Path | Description |
|---|---|---|
| `GET` | `/dashboard` | Aggregate KPIs and low-stock product list |

---

## Deployment URLs

| Service | Local (dev) | Docker (prod) |
|---|---|---|
| Frontend | `http://localhost:5173` | `http://localhost` |
| Backend API | `http://localhost:8000` | `http://localhost/api` |
| API Docs (Swagger) | `http://localhost:8000/docs` | — (internal only) |
| PostgreSQL | `localhost:5432` | `localhost:5432` (if port exposed) |

> In production, expose only port 80/443. Remove the `ports` block from the `backend` service in `docker-compose.yml` and keep the database off the public network.

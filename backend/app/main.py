from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.database import Base, engine
from app.routes import auth, products, customers, orders, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Restrict in production
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix=f"{settings.API_PREFIX}/auth",      tags=["Authentication"])
app.include_router(products.router,  prefix=f"{settings.API_PREFIX}/products",  tags=["Products"])
app.include_router(customers.router, prefix=f"{settings.API_PREFIX}/customers", tags=["Customers"])
app.include_router(orders.router,    prefix=f"{settings.API_PREFIX}/orders",    tags=["Orders"])
app.include_router(dashboard.router, prefix=f"{settings.API_PREFIX}/dashboard", tags=["Dashboard"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

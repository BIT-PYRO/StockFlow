from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routes import products, customers, orders, dashboard, inventory_transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router,               prefix="/products",               tags=["Products"])
app.include_router(customers.router,              prefix="/customers",              tags=["Customers"])
app.include_router(orders.router,                 prefix="/orders",                 tags=["Orders"])
app.include_router(dashboard.router,              prefix="/dashboard",              tags=["Dashboard"])
app.include_router(inventory_transactions.router, prefix="/inventory-transactions", tags=["Inventory Transactions"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "running"}

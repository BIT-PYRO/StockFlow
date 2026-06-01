from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.product import Product, Category
from app.schemas.product import ProductCreate, ProductUpdate, CategoryCreate
from app.schemas.common import PaginatedResponse
from app.utils.pagination import paginate


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Categories ────────────────────────────────────────────────────────────

    def create_category(self, payload: CategoryCreate) -> Category:
        if self.db.query(Category).filter(Category.name == payload.name).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category already exists",
            )
        category = Category(**payload.model_dump())
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def list_categories(self) -> list[Category]:
        return self.db.query(Category).all()

    # ── Products ──────────────────────────────────────────────────────────────

    def create(self, payload: ProductCreate) -> Product:
        if self.db.query(Product).filter(Product.sku == payload.sku).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SKU '{payload.sku}' already exists",
            )
        product = Product(**payload.model_dump())
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def list(
        self,
        page: int,
        page_size: int,
        search: str | None,
        category_id: int | None,
        low_stock: bool,
    ) -> PaginatedResponse[Product]:
        query = self.db.query(Product)
        if search:
            query = query.filter(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.sku.ilike(f"%{search}%"),
                )
            )
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if low_stock:
            query = query.filter(Product.stock_quantity <= Product.reorder_level)
        return paginate(query, page, page_size)

    def get_by_id(self, product_id: int) -> Product:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return product

    def update(self, product_id: int, payload: ProductUpdate) -> Product:
        product = self.get_by_id(product_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product_id: int) -> dict:
        product = self.get_by_id(product_id)
        self.db.delete(product)
        self.db.commit()
        return {"message": "Product deleted successfully"}

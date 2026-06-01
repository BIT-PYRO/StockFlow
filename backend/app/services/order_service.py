import uuid
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderUpdate
from app.schemas.common import PaginatedResponse
from app.utils.pagination import paginate


def _generate_order_number() -> str:
    return f"ORD-{uuid.uuid4().hex[:10].upper()}"


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: OrderCreate) -> Order:
        order = Order(
            order_number=_generate_order_number(),
            customer_id=payload.customer_id,
            discount=payload.discount,
            notes=payload.notes,
        )
        total = Decimal("0.00")

        for item_data in payload.items:
            product: Product = (
                self.db.query(Product).filter(Product.id == item_data.product_id).first()
            )
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product id={item_data.product_id} not found",
                )
            if product.stock_quantity < item_data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}",
                )

            unit_price = product.price
            subtotal = unit_price * item_data.quantity
            total += subtotal

            order.items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=item_data.quantity,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )
            product.stock_quantity -= item_data.quantity

        order.total_amount = max(Decimal("0.00"), total - payload.discount)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def list(
        self,
        page: int,
        page_size: int,
        order_status: OrderStatus | None,
        customer_id: int | None,
    ) -> PaginatedResponse[Order]:
        query = self.db.query(Order)
        if order_status:
            query = query.filter(Order.status == order_status)
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        return paginate(query.order_by(Order.created_at.desc()), page, page_size)

    def get_by_id(self, order_id: int) -> Order:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return order

    def update(self, order_id: int, payload: OrderUpdate) -> Order:
        order = self.get_by_id(order_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(order, field, value)
        self.db.commit()
        self.db.refresh(order)
        return order

    def cancel(self, order_id: int) -> dict:
        order = self.get_by_id(order_id)
        if order.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel an order with status '{order.status}'",
            )
        # Restore stock
        for item in order.items:
            item.product.stock_quantity += item.quantity
        order.status = OrderStatus.CANCELLED
        self.db.commit()
        return {"message": "Order cancelled and stock restored"}

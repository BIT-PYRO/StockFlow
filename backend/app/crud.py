from decimal import Decimal
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, text

from app.models import (
    Product, Customer, Order, OrderItem,
    InventoryTransaction, TransactionType,
    ProductStatus, OrderStatus,
)
from app.schemas import (
    ProductCreate, ProductUpdate,
    CustomerCreate, CustomerUpdate,
    OrderCreate, OrderStatusUpdate,
    InventoryTransactionResponse, InventoryTransactionListResponse,
    RestockRequest, RestockResponse,
    DashboardResponse, LowStockProduct,
)

# Stock level below which a product appears in the low-stock dashboard count.
LOW_STOCK_THRESHOLD = 10


# ── Internal helpers ───────────────────────────────────────────────────────────

def _record_stock_movement(
    db: Session,
    product_id: int,
    txn_type: TransactionType,
    quantity: int,
    notes: str | None = None,
) -> None:
    """
    Append an immutable InventoryTransaction row.
    Called as a side-effect of every stock change; never raises.
    quantity must always be a positive integer — direction is encoded by txn_type.
    """
    db.add(InventoryTransaction(
        product_id=product_id,
        transaction_type=txn_type,
        quantity=quantity,
        notes=notes,
    ))


# ── Products ───────────────────────────────────────────────────────────────────

def get_product(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    return product


def get_products(
    db:       Session,
    skip:     int = 0,
    limit:    int = 100,
    search:   Optional[str]           = None,
    category: Optional[str]           = None,
    status:   Optional[ProductStatus] = None,
    min_price: Optional[Decimal]      = None,
    max_price: Optional[Decimal]      = None,
) -> list[Product]:
    q = db.query(Product)

    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            Product.name.ilike(term) | Product.sku.ilike(term)
        )
    if category:
        q = q.filter(Product.category.ilike(category.strip()))
    if status is not None:
        q = q.filter(Product.status == status)
    if min_price is not None:
        q = q.filter(Product.price >= min_price)
    if max_price is not None:
        q = q.filter(Product.price <= max_price)

    return (
        q
        .order_by(Product.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_product(db: Session, payload: ProductCreate) -> Product:
    # Business rule 1: SKU must be unique across all products.
    if db.query(Product).filter(Product.sku == payload.sku).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with SKU '{payload.sku}' already exists",
        )

    # Business rule 2: price must be greater than zero.
    if payload.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Product price must be greater than zero",
        )

    # Business rule 3: initial stock cannot be negative.
    if payload.stock_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="stock_quantity cannot be negative",
        )

    product = Product(**payload.model_dump())
    db.add(product)
    db.flush()  # obtain product.id before writing the transaction

    # Record initial stock as an IN movement when stock is provided.
    if product.stock_quantity > 0:
        _record_stock_movement(db, product.id, TransactionType.IN, product.stock_quantity)

    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, payload: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    changes = payload.model_dump(exclude_unset=True)

    # Business rule 1: if the SKU is changing, it must not already exist on another product.
    new_sku = changes.get("sku")
    if new_sku is not None and new_sku != product.sku:
        if db.query(Product).filter(Product.sku == new_sku).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with SKU '{new_sku}' already exists",
            )

    # Business rule 2: price must be greater than zero.
    if "price" in changes and changes["price"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Product price must be greater than zero",
        )

    # Business rule 3: stock cannot go negative (also enforced by DB CHECK constraint).
    if "stock_quantity" in changes:
        new_qty = changes["stock_quantity"]
        if new_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="stock_quantity cannot be negative",
            )
        delta = new_qty - product.stock_quantity
        if delta != 0:
            txn_type = TransactionType.IN if delta > 0 else TransactionType.OUT
            _record_stock_movement(db, product.id, txn_type, abs(delta))

    for field, value in changes.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product(db, product_id)

    # Business rule: cannot delete a product that appears in any order.
    # The FK ondelete="RESTRICT" would raise an IntegrityError at the DB level;
    # we guard here to return a readable 409 instead.
    linked = db.query(OrderItem).filter(OrderItem.product_id == product_id).first()
    if linked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Product '{product.name}' cannot be deleted because it is "
                "referenced by one or more orders. Set status to 'inactive' instead."
            ),
        )

    db.delete(product)
    db.commit()


# ── Customers ──────────────────────────────────────────────────────────────────

def get_customer(db: Session, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )
    return customer


def get_customers(db: Session, skip: int = 0, limit: int = 100) -> list[Customer]:
    return (
        db.query(Customer)
        .order_by(Customer.full_name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_customer(db: Session, payload: CustomerCreate) -> Customer:
    # Business rule 2: normalise email to lowercase before any DB operation.
    # EmailStr already validates format at the schema boundary; normalising here
    # provides defence-in-depth for direct CRUD calls that bypass the schema.
    normalised_email = payload.email.lower().strip()

    # Business rule 1: email must be unique (case-insensitive).
    if db.query(Customer).filter(func.lower(Customer.email) == normalised_email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A customer with email '{normalised_email}' is already registered",
        )

    data = payload.model_dump()
    data["email"] = normalised_email  # store in normalised form
    customer = Customer(**data)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer_id: int, payload: CustomerUpdate) -> Customer:
    customer = get_customer(db, customer_id)
    changes = payload.model_dump(exclude_unset=True)

    if "email" in changes:
        # Business rule 2: normalise the incoming email before comparison and storage.
        changes["email"] = changes["email"].lower().strip()

        # Business rule 1: if the email is actually changing, verify it is not taken
        # using a case-insensitive comparison to catch variants like FOO@Bar.com.
        if changes["email"] != customer.email:
            if db.query(Customer).filter(
                func.lower(Customer.email) == changes["email"]
            ).first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{changes['email']}' is already registered to another customer",
                )

    for field, value in changes.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int) -> None:
    customer = get_customer(db, customer_id)

    # Business rule: cannot delete a customer who has placed orders.
    # The FK ondelete="RESTRICT" would raise an IntegrityError at the DB level;
    # we guard here to return a readable 409 instead.
    has_orders = db.query(Order).filter(Order.customer_id == customer_id).first()
    if has_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Customer '{customer.full_name}' cannot be deleted because they "
                "have associated orders. Deactivate the account instead."
            ),
        )

    db.delete(customer)
    db.commit()


# ── Orders ─────────────────────────────────────────────────────────────────────

def get_order(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return order


def get_orders(db: Session, skip: int = 0, limit: int = 100) -> list[Order]:
    return (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_order(db: Session, payload: OrderCreate) -> Order:
    try:
        # Rule 1: customer must exist — raises 404 if not found.
        get_customer(db, payload.customer_id)

        order_items: list[OrderItem] = []
        total_amount = Decimal("0.00")

        for item_data in payload.items:
            # Rule 3: quantity must be greater than zero.
            if item_data.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Quantity for product {item_data.product_id} must be greater than zero",
                )

            # Rule 2: product must exist.
            product = db.query(Product).filter(Product.id == item_data.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {item_data.product_id} not found",
                )

            # Only active products can be ordered.
            if product.status != ProductStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Product '{product.name}' is inactive and cannot be ordered",
                )

            # Rules 4 & 5: stock must be sufficient; reject immediately if not.
            if product.stock_quantity < item_data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Insufficient stock for '{product.name}' (SKU: {product.sku}). "
                        f"Requested: {item_data.quantity}, "
                        f"available: {product.stock_quantity}"
                    ),
                )

            # Rule 8: calculate line total — snapshot unit price at order time so
            # future price changes on the product do not alter historical order data.
            unit_price = Decimal(str(product.price))
            line_total = unit_price * item_data.quantity
            total_amount += line_total  # Rule 9: accumulate order total

            order_items.append(OrderItem(
                product_id=product.id,
                quantity=item_data.quantity,
                price=unit_price,
                line_total=line_total,
            ))

            # Rule 6: deduct stock immediately as part of this transaction.
            product.stock_quantity -= item_data.quantity

        # Rule 9: store the calculated total on the order row.
        order = Order(
            customer_id=payload.customer_id,
            total_amount=total_amount,
            items=order_items,
        )
        db.add(order)

        # Rule 10: flush to resolve IDs within the same DB transaction before
        # writing audit records — no separate commit yet.
        db.flush()

        # Rule 7: record an OUT InventoryTransaction for every order line.
        for item in order.items:
            _record_stock_movement(db, item.product_id, TransactionType.OUT, item.quantity)

        # Rule 10: single commit — all stock changes, order rows, and audit records
        # are written atomically.
        db.commit()
        db.refresh(order)
        return order

    except HTTPException:
        # Rule 11: roll back all in-flight changes on any validation failure so
        # no partial stock deductions or orphaned rows are left in the session.
        db.rollback()
        raise
    except Exception:
        # Rule 11: unexpected DB or runtime errors also trigger a full rollback.
        db.rollback()
        raise


def delete_order(db: Session, order_id: int) -> None:
    order = get_order(db, order_id)

    # Business rule: completed orders are finalised and cannot be deleted.
    if order.order_status == OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order {order_id} is COMPLETED and cannot be deleted",
        )

    # Restore stock for orders that have not yet been cancelled
    # (a CANCELLED order may have already had its stock restored by a prior operation).
    if order.order_status != OrderStatus.CANCELLED:
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock_quantity += item.quantity
                # Record the stock restoration as an IN movement for audit purposes.
                _record_stock_movement(
                    db, item.product_id, TransactionType.IN, item.quantity
                )

    # Cascade on order_items handles removal of child rows automatically.
    db.delete(order)
    db.commit()


# ── Order lifecycle ───────────────────────────────────────────────────────────

# State machine: maps every status to the set of statuses it may transition to.
# Completed and Cancelled are terminal — their sets are empty.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING:   {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


def update_order_status(db: Session, order_id: int, new_status: OrderStatus) -> Order:
    """
    Advance an order through its lifecycle state machine.

    Allowed transitions
    -------------------
    PENDING   → CONFIRMED | CANCELLED
    CONFIRMED → COMPLETED | CANCELLED
    COMPLETED → (terminal — no transitions allowed)
    CANCELLED → (terminal — no transitions allowed)

    Side-effects on CANCELLED
    -------------------------
    * Restores stock_quantity for every order item.
    * Appends an IN InventoryTransaction for each item.
    * All writes are atomic — rolled back on any failure.

    Side-effects on CONFIRMED / COMPLETED
    --------------------------------------
    * No inventory changes: stock was already deducted at order creation.
    """
    try:
        order = get_order(db, order_id)  # raises 404 if not found
        current = order.order_status

        # Business rule: duplicate transition is a no-op conflict, not silent.
        if current == new_status:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Order {order_id} is already in status "
                    f"'{new_status.value}' — no change applied"
                ),
            )

        allowed = _ALLOWED_TRANSITIONS[current]

        # Business rule: terminal states (COMPLETED / CANCELLED) cannot be modified.
        # Business rule: invalid forward jumps (e.g. PENDING → COMPLETED) are rejected.
        if new_status not in allowed:
            allowed_labels = [s.value for s in allowed]
            terminal_msg   = " (terminal state)" if not allowed_labels else ""
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Cannot transition order {order_id} from "
                    f"'{current.value}' to '{new_status.value}'{terminal_msg}. "
                    f"Allowed: {allowed_labels or 'none'}"
                ),
            )

        # Business rule: cancellation restores stock and writes audit records.
        if new_status == OrderStatus.CANCELLED:
            for item in order.items:
                product = (
                    db.query(Product)
                    .filter(Product.id == item.product_id)
                    .first()
                )
                if product:
                    product.stock_quantity += item.quantity
                    _record_stock_movement(
                        db, item.product_id, TransactionType.IN, item.quantity
                    )

        order.order_status = new_status
        db.commit()
        db.refresh(order)
        return order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def restock_product(db: Session, product_id: int, payload: RestockRequest) -> RestockResponse:
    """
    Increase a product's stock_quantity by payload.quantity.

    Side-effects
    ------------
    * Updates Product.stock_quantity atomically.
    * Appends an IN InventoryTransaction with the optional notes field.
    * All writes committed in one transaction; rolled back on any failure.
    """
    try:
        product = get_product(db, product_id)   # raises 404 if not found

        old_stock = product.stock_quantity
        new_stock = old_stock + payload.quantity

        product.stock_quantity = new_stock
        db.flush()   # write product update before inserting transaction

        _record_stock_movement(
            db,
            product_id=product.id,
            txn_type=TransactionType.IN,
            quantity=payload.quantity,
            notes=payload.notes,
        )

        db.commit()
        db.refresh(product)

        return RestockResponse(
            product_id=product.id,
            product_name=product.name,
            old_stock=old_stock,
            added_stock=payload.quantity,
            new_stock=product.stock_quantity,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


# ── Inventory Transactions ─────────────────────────────────────────────────────

def get_inventory_transactions(
    db:               Session,
    product_id:       int | None,
    transaction_type: TransactionType | None,
    start_date:       date | None,
    end_date:         date | None,
    page:             int,
    page_size:        int,
) -> InventoryTransactionListResponse:
    """
    Return a paginated, filtered list of inventory-transaction records with
    computed previous_stock and new_stock fields.

    Stock reconstruction
    --------------------
    We never store previous/new stock snapshots on the transaction row.
    Instead we derive them with a window function:

      signed_delta = +quantity  for IN  / ADJUSTMENT
                   = -quantity  for OUT

      running_total (per product, ordered by created_at, id) =
          SUM(signed_delta) OVER (PARTITION BY product_id ORDER BY created_at, id
                                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

      new_stock      = running_total
      previous_stock = running_total - signed_delta

    This is computed entirely in PostgreSQL in one query — no N+1.
    """
    # ── signed delta expression ────────────────────────────────────────────────
    signed_delta = case(
        (InventoryTransaction.transaction_type == TransactionType.OUT,
         -InventoryTransaction.quantity),
        else_=InventoryTransaction.quantity,
    )

    # ── window: running cumulative stock per product ───────────────────────────
    running_total = func.sum(signed_delta).over(
        partition_by=InventoryTransaction.product_id,
        order_by=[InventoryTransaction.created_at, InventoryTransaction.id],
        rows=(None, 0),         # ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ).label("running_total")

    # ── base query: one row per transaction, joined to product ─────────────────
    # joinedload is not available in core-style queries; use join + columns.
    base = (
        db.query(
            InventoryTransaction.id.label("transaction_id"),
            InventoryTransaction.product_id,
            Product.name.label("product_name"),
            Product.sku,
            InventoryTransaction.transaction_type,
            InventoryTransaction.quantity,
            InventoryTransaction.created_at,
            running_total,
            signed_delta.label("signed_delta"),
        )
        .join(Product, Product.id == InventoryTransaction.product_id)
    )

    # ── filters ────────────────────────────────────────────────────────────────
    if product_id is not None:
        base = base.filter(InventoryTransaction.product_id == product_id)
    if transaction_type is not None:
        base = base.filter(InventoryTransaction.transaction_type == transaction_type)
    if start_date is not None:
        base = base.filter(
            InventoryTransaction.created_at >= text(f"'{start_date}'::timestamptz")
        )
    if end_date is not None:
        # inclusive end: extend to end of the given day
        base = base.filter(
            InventoryTransaction.created_at < text(f"('{end_date}'::date + INTERVAL '1 day')")
        )

    # ── total count (before pagination) ───────────────────────────────────────
    total: int = base.count()

    # ── sort newest-first, paginate ────────────────────────────────────────────
    offset = (page - 1) * page_size
    rows = (
        base
        .order_by(InventoryTransaction.created_at.desc(), InventoryTransaction.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = max(1, -(-total // page_size))   # ceiling division

    transactions = [
        InventoryTransactionResponse(
            transaction_id=row.transaction_id,
            product_id=row.product_id,
            product_name=row.product_name,
            sku=row.sku,
            transaction_type=row.transaction_type,
            quantity=row.quantity,
            previous_stock=int(row.running_total - row.signed_delta),
            new_stock=int(row.running_total),
            created_at=row.created_at,
        )
        for row in rows
    ]

    return InventoryTransactionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        transactions=transactions,
    )


# ── Dashboard ──────────────────────────────────────────────────────────────────

def get_dashboard_stats(db: Session) -> DashboardResponse:
    """
    Return all dashboard KPIs using 3 database round-trips.

    Query 1 — scalar aggregates (products, customers, revenue) via a single
              SELECT with subqueries; avoids multiple round-trips for simple counts.

    Query 2 — order counts broken down by status using GROUP BY in one query.

    Query 3 — low-stock product list (stock_quantity < LOW_STOCK_THRESHOLD),
              ordered by stock ascending so the most critical items appear first.
    """
    # ── Query 1: scalar counts + revenue ──────────────────────────────────────
    total_products  = db.query(func.count(Product.id)).scalar()  or 0
    total_customers = db.query(func.count(Customer.id)).scalar() or 0
    total_revenue   = db.query(
        func.coalesce(func.sum(Order.total_amount), 0)
    ).filter(Order.order_status == OrderStatus.COMPLETED).scalar()

    # ── Query 2: order status breakdown via GROUP BY ───────────────────────────
    status_rows = (
        db.query(Order.order_status, func.count(Order.id))
        .group_by(Order.order_status)
        .all()
    )
    status_counts: dict[OrderStatus, int] = {row[0]: row[1] for row in status_rows}

    total_orders     = sum(status_counts.values())
    pending_orders   = status_counts.get(OrderStatus.PENDING,   0)
    confirmed_orders = status_counts.get(OrderStatus.CONFIRMED, 0)
    completed_orders = status_counts.get(OrderStatus.COMPLETED, 0)
    cancelled_orders = status_counts.get(OrderStatus.CANCELLED, 0)

    # ── Query 3: low-stock product list ───────────────────────────────────────
    low_stock_rows = (
        db.query(Product)
        .filter(Product.stock_quantity < LOW_STOCK_THRESHOLD)
        .order_by(Product.stock_quantity.asc(), Product.name.asc())
        .all()
    )

    return DashboardResponse(
        total_products=total_products,
        total_customers=total_customers,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        confirmed_orders=confirmed_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        low_stock_products=[
            LowStockProduct(
                id=p.id,
                name=p.name,
                sku=p.sku,
                category=p.category,
                stock_quantity=p.stock_quantity,
            )
            for p in low_stock_rows
        ],
    )


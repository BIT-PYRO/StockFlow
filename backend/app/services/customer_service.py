from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.common import PaginatedResponse
from app.utils.pagination import paginate


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: CustomerCreate) -> Customer:
        if self.db.query(Customer).filter(Customer.email == payload.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this email already exists",
            )
        customer = Customer(**payload.model_dump())
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def list(
        self,
        page: int,
        page_size: int,
        search: str | None,
    ) -> PaginatedResponse[Customer]:
        query = self.db.query(Customer)
        if search:
            query = query.filter(
                or_(
                    Customer.full_name.ilike(f"%{search}%"),
                    Customer.email.ilike(f"%{search}%"),
                )
            )
        return paginate(query, page, page_size)

    def get_by_id(self, customer_id: int) -> Customer:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        return customer

    def update(self, customer_id: int, payload: CustomerUpdate) -> Customer:
        customer = self.get_by_id(customer_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def delete(self, customer_id: int) -> dict:
        customer = self.get_by_id(customer_id)
        self.db.delete(customer)
        self.db.commit()
        return {"message": "Customer deleted successfully"}

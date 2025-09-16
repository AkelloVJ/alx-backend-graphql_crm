import re
from decimal import Decimal
from typing import List, Tuple

import graphene
from django.db import IntegrityError, transaction
from django.utils import timezone
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .models import Customer, Product, Order
from crm.models import Product
from .filters import CustomerFilter, ProductFilter, OrderFilter


PHONE_REGEX = re.compile(r"^(\+?\d{7,15}|\d{3}-\d{3}-\d{4})$")


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (graphene.relay.Node,)
        filterset_class = CustomerFilter
        fields = ("id", "name", "email", "phone", "created_at")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (graphene.relay.Node,)
        filterset_class = ProductFilter
        fields = ("id", "name", "price", "stock", "created_at")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = OrderFilter
        fields = ("id", "customer", "products", "total_amount", "order_date", "created_at")


class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    ok = graphene.Boolean()

    @staticmethod
    def validate_customer_payload(name: str, email: str, phone: str | None) -> Tuple[bool, str | None]:
        if not name.strip():
            return False, "Name is required"
        if not email.strip():
            return False, "Email is required"
        if phone and not PHONE_REGEX.match(phone):
            return False, "Invalid phone format"
        return True, None

    @classmethod
    def mutate(cls, root, info, input: CreateCustomerInput):
        is_valid, err = cls.validate_customer_payload(input.name, input.email, input.phone)
        if not is_valid:
            return CreateCustomer(customer=None, message=err, ok=False)
        try:
            customer = Customer.objects.create(name=input.name.strip(), email=input.email.strip(), phone=(input.phone or None))
            return CreateCustomer(customer=customer, message="Customer created", ok=True)
        except IntegrityError:
            return CreateCustomer(customer=None, message="Email already exists", ok=False)


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CreateCustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, input: List[CreateCustomerInput]):
        valid_instances: list[Customer] = []
        errors: list[str] = []

        seen_emails: set[str] = set()
        existing_emails = set(Customer.objects.values_list("email", flat=True))

        for idx, payload in enumerate(input):
            is_valid, err = CreateCustomer.validate_customer_payload(payload.name, payload.email, payload.phone)
            if not is_valid:
                errors.append(f"Index {idx}: {err}")
                continue
            email = payload.email.strip()
            if email in existing_emails or email in seen_emails:
                errors.append(f"Index {idx}: Email already exists")
                continue
            customer = Customer(name=payload.name.strip(), email=email, phone=(payload.phone or None))
            valid_instances.append(customer)
            seen_emails.add(email)

        created: list[Customer] = []
        if valid_instances:
            try:
                with transaction.atomic():
                    created = Customer.objects.bulk_create(valid_instances, ignore_conflicts=True)
            except Exception as e:
                errors.append(str(e))

        return BulkCreateCustomers(customers=created, errors=errors, ok=len(errors) == 0)


class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int(required=False, default_value=0)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    product = graphene.Field(ProductType)
    ok = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, input: CreateProductInput):
        if not input.name.strip():
            return CreateProduct(product=None, ok=False, message="Name is required")
        try:
            price = Decimal(str(input.price))
        except Exception:
            return CreateProduct(product=None, ok=False, message="Invalid price")
        if price <= 0:
            return CreateProduct(product=None, ok=False, message="Price must be positive")
        stock = int(input.stock or 0)
        if stock < 0:
            return CreateProduct(product=None, ok=False, message="Stock cannot be negative")
        product = Product.objects.create(name=input.name.strip(), price=price, stock=stock)
        return CreateProduct(product=product, ok=True, message="Product created")


class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
    order_date = graphene.DateTime(required=False)


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = graphene.Field(OrderType)
    ok = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, input: CreateOrderInput):
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            return CreateOrder(order=None, ok=False, message="Invalid customer ID")

        if not input.product_ids:
            return CreateOrder(order=None, ok=False, message="At least one product must be selected")

        products = list(Product.objects.filter(pk__in=input.product_ids))
        if len(products) != len(set(input.product_ids)):
            return CreateOrder(order=None, ok=False, message="One or more product IDs are invalid")

        order_date = input.order_date or timezone.now()

        with transaction.atomic():
            order = Order.objects.create(customer=customer, order_date=order_date)
            order.products.add(*products)
            order.recalculate_total()
            order.save()

        return CreateOrder(order=order, ok=True, message="Order created")


def _apply_ordering(queryset, order_by_list: list[str], allowed: set[str]):
    if not order_by_list:
        return queryset
    sanitized: list[str] = []
    for item in order_by_list:
        field = item.lstrip("-")
        if field in allowed:
            sanitized.append(item)
    return queryset.order_by(*sanitized) if sanitized else queryset


class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")

    all_customers = DjangoFilterConnectionField(
        CustomerType,
        order_by=graphene.List(graphene.String, description="Fields to order by, e.g., name or -created_at"),
    )
    all_products = DjangoFilterConnectionField(
        ProductType,
        order_by=graphene.List(graphene.String, description="Fields to order by, e.g., price or -stock"),
    )
    all_orders = DjangoFilterConnectionField(
        OrderType,
        order_by=graphene.List(graphene.String, description="Fields to order by, e.g., -order_date or total_amount"),
    )

    def resolve_all_customers(self, info, **kwargs):
        order_by = kwargs.pop("order_by", None)
        qs = Customer.objects.all()
        return _apply_ordering(qs, order_by or [], {"name", "email", "created_at"})

    def resolve_all_products(self, info, **kwargs):
        order_by = kwargs.pop("order_by", None)
        qs = Product.objects.all()
        return _apply_ordering(qs, order_by or [], {"name", "price", "stock", "created_at"})

    def resolve_all_orders(self, info, **kwargs):
        order_by = kwargs.pop("order_by", None)
        qs = Order.objects.all().distinct()
        return _apply_ordering(qs, order_by or [], {"order_date", "total_amount", "created_at"})


class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        increment_by = graphene.Int(required=False, default_value=10)

    updated_products = graphene.List(ProductType)
    message = graphene.String()
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, increment_by: int = 10):
        try:
            increment = max(0, int(increment_by))
        except Exception:
            increment = 10
        low_stock = list(Product.objects.filter(stock__lt=10))
        if not low_stock:
            return UpdateLowStockProducts(updated_products=[], message="No low-stock products", ok=True)
        for product in low_stock:
            product.stock = product.stock + increment
        Product.objects.bulk_update(low_stock, ["stock"]) 
        return UpdateLowStockProducts(updated_products=low_stock, message=f"Updated {len(low_stock)} products", ok=True)


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    update_low_stock_products = UpdateLowStockProducts.Field()

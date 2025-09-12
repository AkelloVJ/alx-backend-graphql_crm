#!/usr/bin/env python3
import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product, Order  # noqa: E402
from django.utils import timezone  # noqa: E402


def run():
    Customer.objects.all().delete()
    Product.objects.all().delete()
    Order.objects.all().delete()

    alice = Customer.objects.create(name="Alice", email="alice@example.com", phone="+1234567890")
    bob = Customer.objects.create(name="Bob", email="bob@example.com")

    laptop = Product.objects.create(name="Laptop", price=Decimal("999.99"), stock=10)
    mouse = Product.objects.create(name="Mouse", price=Decimal("25.50"), stock=100)

    order = Order.objects.create(customer=alice, order_date=timezone.now())
    order.products.add(laptop, mouse)
    order.recalculate_total()
    order.save()

    print("Seeded customers:", Customer.objects.count())
    print("Seeded products:", Product.objects.count())
    print("Seeded orders:", Order.objects.count())


if __name__ == "__main__":
    run()

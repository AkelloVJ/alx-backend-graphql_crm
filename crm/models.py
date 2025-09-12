from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.price})"


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    products = models.ManyToManyField(Product, related_name="orders")
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    order_date = models.DateTimeField(default=timezone.now)

    def recalculate_total(self) -> None:
        total = Decimal("0.00")
        for product in self.products.all():
            total += product.price
        # Normalize to 2 dp
        self.total_amount = total.quantize(Decimal("0.01"))

    def __str__(self):
        return f"Order #{self.pk} - {self.customer} - {self.total_amount}"

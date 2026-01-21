from decimal import Decimal
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class TableReservation(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)

    date = models.DateField()
    time = models.TimeField()
    people = models.PositiveIntegerField()

    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[("new", "New"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        default="new",
    )

    def __str__(self):
        return f"{self.name} - {self.date} {self.time} ({self.people})"


# -----------------------------
# EXTRA DETAILS / OPTIONS
# -----------------------------

class OptionGroup(models.Model):
    """
    Example groups: Sauce, Size, Extras
    """
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)

    # selection rules (defaults, can be overridden per product)
    is_required = models.BooleanField(default=False)
    min_select = models.PositiveIntegerField(default=0)
    max_select = models.PositiveIntegerField(default=1)  # 1 = radio, >1 = checkboxes

    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Option(models.Model):
    """
    Example options:
      Sauce group -> Garlic, Spicy
      Size group  -> Small, Large (+1.50)
      Extras      -> Cheese (+1.00)
    """
    group = models.ForeignKey(OptionGroup, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=120)
    price_delta = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        sign = "+" if self.price_delta >= 0 else ""
        return f"{self.group.name}: {self.name} ({sign}{self.price_delta}€)"


class ProductOptionGroup(models.Model):
    """
    Attach option groups to a product and optionally override rules per product.
    Example: Döner -> Sauce (required, choose 1), Extras (optional, choose up to 3)
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_option_groups")
    group = models.ForeignKey(OptionGroup, on_delete=models.PROTECT)

    # overrides (if null -> use group defaults)
    is_required = models.BooleanField(null=True, blank=True)
    min_select = models.PositiveIntegerField(null=True, blank=True)
    max_select = models.PositiveIntegerField(null=True, blank=True)

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "group")
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.product.name} -> {self.group.name}"

    def effective_is_required(self) -> bool:
        return self.is_required if self.is_required is not None else self.group.is_required

    def effective_min_select(self) -> int:
        return self.min_select if self.min_select is not None else self.group.min_select

    def effective_max_select(self) -> int:
        return self.max_select if self.max_select is not None else self.group.max_select


# -----------------------------
# ORDERING
# -----------------------------

class Order(models.Model):
    STATUS_CHOICES = (
        ("CART", "Cart"),
        ("PLACED", "Placed"),
        ("PREPARING", "Preparing"),
        ("DELIVERING", "Delivering"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True)

    address_line = models.CharField(max_length=255, blank=True)  # for delivery
    city = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="CART")
    created_at = models.DateTimeField(auto_now_add=True)
    placed_at = models.DateTimeField(null=True, blank=True)

    payment_method = models.CharField(max_length=20, blank=True)  # "CASH" or "STRIPE"
    is_paid = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)

    order_number = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)

    def ensure_order_number(self):
        if not self.order_number:
            # Example: OK-20260113-7F3A2B
            self.order_number = f"OK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


    def total_price(self):
        return sum(item.total_price() for item in self.items.all())

    def __str__(self):
        return f"Order #{self.id} - {self.status}"


class OrderItem(models.Model):
    """
    NOTE:
    - We DO NOT use unique_together(order, product) anymore because:
      same product with different options must be separate lines.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price_at_time = models.DecimalField(max_digits=8, decimal_places=2)

    def options_total(self):
        # options_total for ONE unit
        return sum(o.price_delta_at_time for o in self.chosen_options.all())

    def unit_total(self):
        # base + options for ONE unit
        return self.price_at_time + self.options_total()

    def total_price(self):
        # unit_total * quantity
        return self.unit_total() * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class OrderItemOption(models.Model):
    """
    Stores chosen options per order item (snapshot price delta at the time).
    """
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="chosen_options")
    option = models.ForeignKey(Option, on_delete=models.PROTECT)
    price_delta_at_time = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ("order_item", "option")

    def __str__(self):
        return f"{self.order_item} - {self.option.group.name}: {self.option.name}"


class Event(models.Model):
    """
    Event model for displaying events on the website.
    Example: "Individuelle Feiern" (Individual Celebrations), "Private Feiern" (Private Celebrations)
    """
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="events/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return f"{self.title} (€{self.price})"

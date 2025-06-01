from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from ckeditor.fields import RichTextField
from decimal import Decimal
from tinymce.models import HTMLField
import random
import string
from django.conf import settings
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator

def generate_order_code():
    return uuid.uuid4().hex[:8].upper()

class ProductCharacteristicValue(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='characteristic_values')
    characteristic = models.ForeignKey('CategoryCharacteristic', on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.characteristic.name}: {self.value}"

    class Meta:
        verbose_name = "Характеристика товара"
        verbose_name_plural = "Характеристики товара"

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='product_images/')
    rich_description = HTMLField(blank=True, null=True)
    rich_specs = HTMLField(blank=True, null=True, verbose_name="Характеристики (rich)")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return sum(item.total_price() for item in self.items.all())

    def __str__(self):
        return f"Cart {self.id} - {self.user if self.user else 'Anonymous'}"

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selected_characteristics = models.ManyToManyField(ProductCharacteristicValue, blank=True)

    def total_price(self):
        base_price = self.final_price if self.final_price else self.product.base_price
        for characteristic in self.selected_characteristics.all():
            base_price += getattr(characteristic, 'price_modifier', 0)
        return base_price * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    class Meta:
        verbose_name = "Товар в корзине"
        verbose_name_plural = "Товары в корзине"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(null=True, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"Профиль {self.user.username}"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/extra/')

    def __str__(self):
        return f"Изображение для {self.product.name}"

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField()
    active = models.BooleanField(default=True)
    is_birthday = models.BooleanField(default=False)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='promo_codes')  # ← добавили

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Принят'),
        ('ready', 'Готов к получению'),
        ('done', 'Выдан'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    pickup_location = models.CharField(max_length=255, null=True, blank=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[("cash", "Наличными"), ("card", "Картой")],
        default="cash"
    )
    code = models.CharField(max_length=10, unique=True, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус заказа'
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Заказ {self.id} ({self.code}) — {self.get_status_display()}"

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    final_price = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}×{self.product.name} in order #{self.order.pk}"

    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"

class CategoryCharacteristic(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='characteristics')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.category.name} — {self.name}"

    class Meta:
        verbose_name = "Характеристика категории"
        verbose_name_plural = "Характеристики категорий"

class ProductReview(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    photo = models.ImageField(upload_to='review_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} — {self.rating}★"

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import PromoCode, Category, Product, ProductImage, UserProfile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from tinymce.widgets import TinyMCE
from .models import CategoryCharacteristic, ProductCharacteristicValue
from .models import Order, OrderItem
from .models import Cart, CartItem
from .models import ProductReview

@admin.register(CategoryCharacteristic)
class CategoryCharacteristicAdmin(admin.ModelAdmin):
    list_display = ('category', 'name')
    list_filter = ('category',)

@admin.register(ProductCharacteristicValue)
class ProductCharacteristicValueAdmin(admin.ModelAdmin):
    list_display = ('product', 'get_characteristic_name', 'get_value')
    list_filter = ('characteristic',)

    def get_characteristic_name(self, obj):
        return obj.characteristic.name
    get_characteristic_name.short_description = 'Характеристика'

    def get_value(self, obj):
        return obj.value
    get_value.short_description = 'Значение'


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'rich_description': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'rich_specs': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductCharacteristicValueInline(admin.TabularInline):
    model = ProductCharacteristicValue
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'category', 'base_price')
    list_filter = ('category',)
    search_fields = ('name',)

    inlines = [ProductImageInline, ProductCharacteristicValueInline]  # ← добавили характеристику

    readonly_fields = ('preview_image',)

    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'base_price', 'image', 'preview_image')
        }),
        ('Описание товара', {
            'fields': ('rich_description', 'rich_specs'),
            'classes': ('collapse',)
        }),
    )

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" style="border-radius:10px;">', obj.image.url)
        return "Нет изображения"
    preview_image.short_description = "Превью"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'used_count', 'usage_limit', 'is_birthday', 'active')
    list_filter = ('is_birthday', 'active')
    search_fields = ('code',)
    readonly_fields = ('used_count',)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль пользователя'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'final_price')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'code', 'status', 'created_at', 'pickup_location', 'payment_method')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('code', 'user__username')
    inlines = [OrderItemInline]
    readonly_fields = ('code', 'created_at')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at', 'rating')
    search_fields = ('product__name', 'user__username', 'comment')
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Выбранные отзывы одобрены.")
    approve_reviews.short_description = "Одобрить выбранные отзывы"

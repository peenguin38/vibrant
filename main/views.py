from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Category, Product, Cart, CartItem, ProductImage
from django.db.models import Q
from .forms import CustomRegisterForm
from .models import UserProfile
from django.utils import timezone
from .models import PromoCode
from decimal import Decimal
from django.contrib import messages
from .models import Order, OrderItem
from .models import CategoryCharacteristic, ProductCharacteristicValue
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import uuid
import os
from django.conf import settings
from .models import ProductReview
from collections import Counter
from main.models import Product

def get_cart(request):
    """Получает текущую корзину пользователя или создает новую"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


@csrf_exempt
@require_POST
def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'unauthenticated', 'message': 'Требуется вход в аккаунт'}, status=401)

    product = get_object_or_404(Product, id=product_id)
    promo_code = request.POST.get('promo_code')

    final_price = product.base_price
    promo_discount = None

    if promo_code:
        try:
            promo = PromoCode.objects.get(code=promo_code, active=True, user=request.user)
            if promo.usage_limit is None or promo.used_count < promo.usage_limit:
                discount_amount = product.base_price * (Decimal(promo.discount_percent) / Decimal('100'))
                final_price -= discount_amount
                promo_discount = promo.discount_percent

                promo.used_count += 1
                promo.save()
            else:
                return JsonResponse({'status': 'error', 'message': 'Промокод превышает лимит использования'})
        except PromoCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Неверный или неактивный промокод'})

    cart = get_cart(request)
    cart_item = CartItem.objects.filter(cart=cart, product=product, final_price=final_price).first()

    if cart_item:
        cart_item.quantity += 1
        created = False
    else:
        cart_item = CartItem.objects.create(cart=cart, product=product, quantity=1, final_price=final_price)
        created = True

    cart_item.save()

    return JsonResponse({'status': 'success', 'message': 'Товар добавлен в корзину'})


def cart_view(request):
    """Отображает страницу корзины"""
    cart = get_cart(request)
    cart_items = cart.items.all()
    total_price = cart.total_price()

    return render(request, 'main/cart.html', {"cart_items": cart_items, "total_price": total_price})


def index(request):
    categories = Category.objects.all()
    birthday_today = False
    birthday_promo = None

    latest_products = Product.objects.order_by('-id')[:5]

    macmini = Product.objects.filter(name__icontains="Mac mini").first()

    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and profile.date_of_birth:
            today = timezone.now().date()
            if today.month == profile.date_of_birth.month and today.day == profile.date_of_birth.day:
                birthday_promo_obj, created = PromoCode.objects.get_or_create(
                    user=request.user,
                    is_birthday=True,
                    defaults={
                        'code': f"BIRTHDAY-{uuid.uuid4().hex[:6].upper()}",
                                'discount_percent': 5,
                'usage_limit': 1,
                'active': True,
                }
                )

                if birthday_promo_obj.used_count < (birthday_promo_obj.usage_limit or 1):
                    birthday_today = True
                    birthday_promo = birthday_promo_obj

    macmini = Product.objects.filter(name__icontains="Mac Mini").first()

    return render(request, 'main/index.html', {
        'categories': categories,
        'birthday_today': birthday_today,
        'birthday_promo': birthday_promo,
        'latest_products': latest_products,
        'macmini': macmini,
    })


def search_results(request):
    query = request.GET.get("q")
    categories = Category.objects.all()

    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.none()

    return render(request, "main/search_results.html", {"query": query, "products": products, "categories": categories})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Неверный логин или пароль')
            return redirect('login')
    return render(request, 'main/login.html')


def register_view(request):
    if request.method == "POST":
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            user.profile.date_of_birth = form.cleaned_data['date_of_birth']
            user.profile.save()

            login(request, user)
            return redirect('index')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = CustomRegisterForm()
    return render(request, 'main/register.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('index')
    return render(request, 'main/logout.html')

def category_products(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    categories = Category.objects.all()
    products = Product.objects.filter(category=category)

    sort_option = request.GET.get('sort')
    if sort_option == 'price_asc':
        products = products.order_by('base_price')
    elif sort_option == 'price_desc':
        products = products.order_by('-base_price')

    characteristics = CategoryCharacteristic.objects.filter(category=category)
    selected_filters = {}
    filter_values = {}

    for char in characteristics:
        char_name = char.name
        values = request.GET.getlist(f'filter_{char_name}')
        if values:
            selected_filters[char_name] = values
            products = products.filter(
                characteristic_values__characteristic__name=char_name,
                characteristic_values__value__in=values
            ).distinct()

        all_values = ProductCharacteristicValue.objects.filter(
            product__category=category,
            characteristic=char
        ).values_list('value', flat=True).distinct()

        filter_values[char_name] = list(all_values)

    return render(request, 'main/category_products.html', {
        'category': category,
        'products': products,
        'categories': categories,
        'characteristics': characteristics,
        'selected_filters': selected_filters,
        'filter_values': filter_values,
    })



def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    promo_code = request.GET.get('promo')
    final_price = product.base_price
    promo_discount = None
    invalid_promo = False

    if request.method == "POST" and request.user.is_authenticated:
        rating = int(request.POST.get("rating"))
        comment = request.POST.get("comment")
        photo = request.FILES.get("photo")

        ProductReview.objects.create(
            product=product,
            user=request.user,
            rating=rating,
            comment=comment,
            photo=photo
        )
        return redirect(request.path_info)

    if promo_code:
        try:
            promo = PromoCode.objects.get(code=promo_code, active=True, user=request.user)
            if promo.usage_limit is None or promo.used_count < promo.usage_limit:
                discount_amount = product.base_price * (Decimal(promo.discount_percent) / Decimal(100))
                final_price = product.base_price - discount_amount
                promo_discount = promo.discount_percent
            else:
                invalid_promo = True
        except PromoCode.DoesNotExist:
            invalid_promo = True

    approved_reviews = product.reviews.filter(is_approved=True).order_by('-created_at')

    distribution_count = Counter(str(r.rating) for r in approved_reviews)
    total_reviews = sum(distribution_count.values()) or 1

    distribution_percent = {
        str(star): round((distribution_count.get(str(star), 0) / total_reviews) * 100, 1)
        for star in range(1, 6)
    }

    context = {
        'product': product,
        'images': product.images.all(),
        'characteristics': product.characteristic_values.all(),
        'final_price': final_price,
        'promo_discount': promo_discount,
        'invalid_promo': invalid_promo,
        'promo_code': promo_code,
        'reviews': approved_reviews,
        'star_distribution': distribution_percent,
        'star_distribution_count': distribution_count,
        'star_range': ['5', '4', '3', '2', '1'],
        'distribution_percent': distribution_percent,
    }

    return render(request, 'main/product_detail.html', context)



def update_quantity(request, item_id):
    change = int(request.GET.get("change", 0))
    cart = get_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if change == -1 and item.quantity == 1:
        item.delete()
        return JsonResponse({"status": "removed", "quantity": 0})
    else:
        item.quantity = max(1, item.quantity + change)
        item.save()
        return JsonResponse({"status": "updated", "quantity": item.quantity})

@login_required
def checkout_view(request):
    if request.method != 'POST':
        return redirect('cart')

    cart = get_cart(request)
    if not cart.items.exists():
        messages.error(request, "Корзина пуста.")
        return redirect('cart')

    order = Order.objects.create(user=request.user)

    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            final_price=item.final_price
        )

    cart.items.all().delete()

    messages.success(request, "Заказ оформлен! Спасибо за покупку ❤️")
    return redirect('order_success')


@login_required
def order_success(request):
    order_id = request.session.get("last_order_id")
    order = None
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            pass

    return render(request, "main/order_success.html", {"order": order})


def about_view(request):
    return render(request, 'main/about.html')

from .models import Order

from django.contrib.auth import update_session_auth_hash

@login_required
def profile_view(request):
    user = request.user

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    if request.method == "POST":
        username = request.POST.get("username")
        last_name = request.POST.get("last_name")
        middle_name = request.POST.get("middle_name")
        email = request.POST.get("email")
        new_password = request.POST.get("new_password")

        user.username = username
        user.email = email
        profile.last_name = last_name
        profile.middle_name = middle_name

        if new_password:
            user.set_password(new_password)
            update_session_auth_hash(request, user)

        user.save()
        profile.save()

        messages.success(request, "Изменения сохранены")

    orders = Order.objects.filter(user=user) \
        .order_by('-created_at') \
        .prefetch_related('items__product')

    for order in orders:
        order.total_price = sum(item.final_price * item.quantity for item in order.items.all())

    return render(request, 'main/profile.html', {
        'user_orders': orders,
    })


@require_GET
def remove_from_cart(request, item_id):
    cart = get_cart(request)
    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
        item.delete()
        return JsonResponse({"status": "removed"})
    except CartItem.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Товар не найден"}, status=404)


@csrf_exempt
@login_required
def order_view(request):
    cart = get_cart(request)
    items = cart.items.all()
    total = cart.total_price()

    pickup_points = [
        {"coords": [55.751574, 37.573856], "label": "Москва, центр",       "hours": "9:00–21:00"},
        {"coords": [55.774532, 37.632645], "label": "ТЦ «Европейский»",  "hours": "9:00–21:00"},
        {"coords": [55.707972, 37.579178], "label": "ул. Ленинская, 12", "hours": "9:00–21:00"},
    ]

    order = None

    if request.method == "POST":
        addr = request.POST.get("pickup_location")
        payment = request.POST.get("payment_method")

        if not addr:
            messages.error(request, "Выберите пункт самовывоза")
            return redirect("order")

        order = Order.objects.create(
            user=request.user,
            pickup_location=addr,
            payment_method=payment
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                final_price=item.final_price
            )

        cart.items.all().delete()

        request.session['last_order_id'] = order.id
        return redirect("order_success")

    return render(request, 'main/order.html', {
        "cart_items": items,
        "total_price": total,
        "pickup_points": pickup_points,
        "order": order
    })

@csrf_exempt
def tinymce_image_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        image = request.FILES['file']
        filename = f"{uuid.uuid4().hex}_{image.name}"
        save_path = os.path.join(settings.MEDIA_ROOT, 'tinymce_uploads', filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)

        image_url = f"{settings.MEDIA_URL}tinymce_uploads/{filename}"
        return JsonResponse({'location': image_url})

    return JsonResponse({'error': 'Ошибка загрузки'}, status=400)



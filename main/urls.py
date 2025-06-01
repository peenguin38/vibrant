from . import views
from .views import login_view, register_view, logout_view
from .views import category_products, add_to_cart, product_detail
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from .views import remove_from_cart


urlpatterns = [
    path('', views.index, name='index'),
    path("search/", views.search_results, name="search_results"),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('category/<slug:category_slug>/', category_products, name='category_products'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('product/<int:pk>/', product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('cart/update_quantity/<int:item_id>/', views.update_quantity, name='update_quantity'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('about/', views.about_view, name='about'),
    path('profile/', views.profile_view, name='profile'),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('tinymce/', include('tinymce.urls')),
    path('order/', views.order_view, name='order'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)




from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('admin/', views.admin_panel, name='admin'),

    # Menu / Categories / Products
    #path('menu/', views.menu, name='menu'),
    #path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    #path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Cart
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/count/", views.get_cart_count, name="get_cart_count"),
    path("checkout/", views.checkout, name="checkout"),
    #path('cart/update/<int:product_id>/', views.update_cart_item, name='update_cart_item'),

     # ✅ payment
    path("checkout/create-session/", views.create_stripe_checkout_session, name="create_stripe_checkout_session"),
    path("checkout/success/", views.checkout_success, name="checkout_success"),
    path("checkout/cancel/", views.checkout_cancel, name="checkout_cancel"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("checkout/save-info/", views.save_checkout_info, name="save_checkout_info"),
    path("checkout/cash/", views.place_cash_order, name="place_cash_order"),
    path("order/success/<str:order_number>/", views.order_success, name="order_success"),
    path("order/track/", views.track_order, name="track_order"),

# Reservation
    path("reservation/create/", views.create_reservation, name="create_reservation"),




]

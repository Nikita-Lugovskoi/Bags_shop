from django.urls import path
from . import views

app_name = 'bags'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('popular/', views.popular_products, name='popular_products'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.product_list, name='product_list_by_category'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<int:order_id>/', views.payment, name='payment'),
    path('payment/process/<int:order_id>/', views.process_payment, name='process_payment'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/edit/<int:order_id>/', views.edit_order, name='edit_order'),
    path('orders/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('favorites/', views.favorites, name='favorites'),
    path('favorites/add/<int:product_id>/', views.add_to_favorites, name='add_to_favorites'),
    path('favorites/remove/<int:product_id>/', views.remove_from_favorites, name='remove_from_favorites'),
    path('review/add/<int:pk>/', views.add_review, name='add_review'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('review/vote/<int:review_id>/', views.vote_review, name='vote_review'),
    path('order/submitted/', views.order_submitted, name='order_submitted'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
]

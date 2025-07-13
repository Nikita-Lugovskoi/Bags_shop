from decimal import Decimal
from .models import Order, OrderItem


def cart(request):
    """
    Добавляет информацию о корзине в контекст шаблонов
    """
    cart_items = []
    total_price = Decimal('0.00')
    total_items = 0

    if request.user.is_authenticated:
        # Получаем активный заказ пользователя (статус 'new')
        active_order = Order.objects.filter(
            user=request.user,
            status='new'
        ).first()

        if active_order:
            # Получаем все товары в корзине
            cart_items = OrderItem.objects.filter(order=active_order)

            # Считаем общую стоимость и количество позиций (каждый товар как отдельная позиция)
            for item in cart_items:
                total_price += item.price * item.quantity
                total_items += 1  # Каждый товар как отдельная позиция

    return {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_items': total_items,
        'cart_items_count': total_items,  # Для совместимости с шаблоном
    }

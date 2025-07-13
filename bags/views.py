from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
# from django.utils.safestring import mark_safe
from .models import Category, Product, Order, OrderItem, Favorite, Review, ReviewVote
from .forms import OrderForm, EditOrderForm, ReviewForm
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
# from django.db.models import Avg
# from .cart import Cart
from django.db import models
from django.core.mail import send_mail
from .utils import limit_user_carts


def get_cached_categories():
    """
    Получение списка категорий из кэша или базы данных
    """
    if settings.CACHE_ENABLED:
        categories = cache.get('categories')
        if categories is None:
            categories = list(Category.objects.all())
            cache.set('categories', categories, timeout=60 * 60 * 24)  # 24 часа
        return categories
    return Category.objects.all()


def get_cached_product(product_id):
    """
    Получение информации о товаре из кэша или базы данных
    """
    if settings.CACHE_ENABLED:
        cache_key = f'product_{product_id}'
        product = cache.get(cache_key)
        if product is None:
            product = get_object_or_404(Product, id=product_id, in_stock=True)
            cache.set(cache_key, product, timeout=60 * 60 * 12)  # 12 часов
        return product
    return get_object_or_404(Product, id=product_id, in_stock=True)


def get_cached_filter_data():
    """
    Получение данных для фильтров из кэша или базы данных
    """
    if settings.CACHE_ENABLED:
        cache_key = 'filter_data'
        filter_data = cache.get(cache_key)
        if filter_data is None:
            # Для фильтра по материалу: список уникальных материалов
            raw_materials = Product.objects.exclude(materials='').values_list('materials', flat=True)
            material_set = set()
            for entry in raw_materials:
                for mat in entry.replace(';', ',').replace('/', ',').split(','):
                    mat = mat.strip()
                    if mat:
                        material_set.add(mat)
            all_materials = sorted(material_set)

            # Для фильтра по цвету бусин: список уникальных цветов
            raw_colors = Product.objects.exclude(bead_color='').values_list('bead_color', flat=True)
            color_set = set()
            for entry in raw_colors:
                for color in entry.replace(';', ',').replace('/', ',').split(','):
                    color = color.strip()
                    if color:
                        color_set.add(color)
            all_colors = sorted(color_set)

            # Для фильтра по цвету фурнитуры: список уникальных цветов
            raw_hardware_colors = Product.objects.exclude(hardware_color='').values_list('hardware_color', flat=True)
            hardware_color_set = set()
            for entry in raw_hardware_colors:
                for color in entry.replace(';', ',').replace('/', ',').split(','):
                    color = color.strip()
                    if color:
                        hardware_color_set.add(color)
            all_hardware_colors = sorted(hardware_color_set)

            filter_data = {
                'all_materials': all_materials,
                'all_colors': all_colors,
                'all_hardware_colors': all_hardware_colors,
            }
            cache.set(cache_key, filter_data, timeout=60 * 60 * 6)  # 6 часов
        return filter_data

    # Если кэширование отключено, возвращаем данные напрямую
    raw_materials = Product.objects.exclude(materials='').values_list('materials', flat=True)
    material_set = set()
    for entry in raw_materials:
        for mat in entry.replace(';', ',').replace('/', ',').split(','):
            mat = mat.strip()
            if mat:
                material_set.add(mat)
    all_materials = sorted(material_set)

    raw_colors = Product.objects.exclude(bead_color='').values_list('bead_color', flat=True)
    color_set = set()
    for entry in raw_colors:
        for color in entry.replace(';', ',').replace('/', ',').split(','):
            color = color.strip()
            if color:
                color_set.add(color)
    all_colors = sorted(color_set)

    raw_hardware_colors = Product.objects.exclude(hardware_color='').values_list('hardware_color', flat=True)
    hardware_color_set = set()
    for entry in raw_hardware_colors:
        for color in entry.replace(';', ',').replace('/', ',').split(','):
            color = color.strip()
            if color:
                hardware_color_set.add(color)
    all_hardware_colors = sorted(hardware_color_set)

    return {
        'all_materials': all_materials,
        'all_colors': all_colors,
        'all_hardware_colors': all_hardware_colors,
    }


def get_cached_popular_products():
    """
    Получение популярных товаров из кэша или базы данных
    """
    if settings.CACHE_ENABLED:
        cache_key = 'popular_products'
        products = cache.get(cache_key)
        if products is None:
            products = list(Product.objects.filter(is_popular=True).order_by('-created_at'))
            cache.set(cache_key, products, timeout=60 * 60 * 2)  # 2 часа
        return products
    return Product.objects.filter(is_popular=True).order_by('-created_at')


def get_cached_latest_products(limit=8):
    """
    Получение последних товаров из кэша или базы данных
    """
    if settings.CACHE_ENABLED:
        cache_key = f'latest_products_{limit}'
        products = cache.get(cache_key)
        if products is None:
            products = list(Product.objects.all().order_by('-created_at')[:limit])
            cache.set(cache_key, products, timeout=60 * 30)  # 30 минут
        return products
    return Product.objects.all().order_by('-created_at')[:limit]


def get_cached_similar_products(product, limit=15):
    """
    Получение похожих товаров из кэша или базы данных
    """
    if settings.CACHE_ENABLED:
        cache_key = f'similar_products_{product.id}_{limit}'
        products = cache.get(cache_key)
        if products is None:
            products = list(Product.objects.filter(category=product.category).exclude(id=product.id)[:limit])
            cache.set(cache_key, products, timeout=60 * 60)  # 1 час
        return products
    return Product.objects.filter(category=product.category).exclude(id=product.id)[:limit]


def get_cached_site_stats():
    """
    Получение статистики сайта из кэша или базы данных
    """
    if settings.CACHE_ENABLED:
        cache_key = 'site_stats'
        stats = cache.get(cache_key)
        if stats is None:
            stats = {
                'total_products': Product.objects.count(),
                'popular_products_count': Product.objects.filter(is_popular=True).count(),
                'categories_count': Category.objects.count(),
                'total_views': Product.objects.aggregate(total_views=models.Sum('views_count'))['total_views'] or 0,
            }
            cache.set(cache_key, stats, timeout=60 * 60)  # 1 час
        return stats

    # Если кэширование отключено, возвращаем данные напрямую
    return {
        'total_products': Product.objects.count(),
        'popular_products_count': Product.objects.filter(is_popular=True).count(),
        'categories_count': Category.objects.count(),
        'total_views': Product.objects.aggregate(total_views=models.Sum('views_count'))['total_views'] or 0,
    }


def home(request):
    """
    Главная страница магазина
    """
    latest_products = get_cached_latest_products(8)
    categories = get_cached_categories()
    site_stats = get_cached_site_stats()
    return render(request, 'bags/home.html', {
        'latest_products': latest_products,
        'categories': categories,
        'site_stats': site_stats,
    })


def product_list(request, category_id=None):
    """
    Страница со списком всех товаров
    """
    categories = Category.objects.all()
    products = Product.objects.all()

    # Поиск по названию и описанию
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(materials__icontains=search_query) |
            Q(bead_color__icontains=search_query) |
            Q(hardware_color__icontains=search_query)
        )

    # Фильтрация по категории
    if category_id:
        products = products.filter(category_id=category_id)
    else:
        category_id = request.GET.get('category')
        if category_id:
            products = products.filter(category_id=category_id)

    # Фильтр "Только в наличии"
    in_stock = request.GET.get('in_stock')
    if in_stock == 'on':
        products = products.filter(in_stock=True)

    # Фильтр по цене
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        products = products.filter(price__gte=price_min)
    if price_max:
        products = products.filter(price__lte=price_max)

    # Фильтр по материалу
    material = request.GET.get('material')
    if material:
        products = products.filter(materials__icontains=material)

    # Фильтр по размерам
    height_min = request.GET.get('height_min')
    height_max = request.GET.get('height_max')
    length_min = request.GET.get('length_min')
    length_max = request.GET.get('length_max')
    depth_min = request.GET.get('depth_min')
    depth_max = request.GET.get('depth_max')
    if height_min:
        products = products.filter(height__gte=height_min)
    if height_max:
        products = products.filter(height__lte=height_max)
    if length_min:
        products = products.filter(length__gte=length_min)
    if length_max:
        products = products.filter(length__lte=length_max)
    if depth_min:
        products = products.filter(depth__gte=depth_min)
    if depth_max:
        products = products.filter(depth__lte=depth_max)

    # Фильтр по цвету бусин
    bead_color = request.GET.get('bead_color')
    if bead_color:
        products = products.filter(bead_color__iexact=bead_color)

    # Фильтр по цвету фурнитуры
    hardware_color = request.GET.get('hardware_color')
    if hardware_color:
        products = products.filter(hardware_color__iexact=hardware_color)

    # Пагинация
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    # Получаем кэшированные данные для фильтров
    filter_data = get_cached_filter_data()

    return render(request, 'bags/product_list.html', {
        'categories': categories,
        'products': products,
        'search_query': search_query,
        'all_materials': filter_data['all_materials'],
        'all_colors': filter_data['all_colors'],
        'all_hardware_colors': filter_data['all_hardware_colors'],
    })


def product_detail(request, slug):
    """
    Представление для отображения детальной информации о товаре
    """
    product = get_object_or_404(Product, slug=slug)

    # Увеличиваем счетчик просмотров
    product.views_count += 1
    product.save()

    # Проверяем, нужно ли отметить товар как популярный
    if product.views_count >= 20 and not product.is_popular:  # Порог в 20 просмотров
        product.is_popular = True
        product.save()

    reviews = product.review_set.filter(is_approved=True).order_by('-created_at')

    # Пагинация отзывов
    paginator = Paginator(reviews, 5)
    page = request.GET.get('page')
    reviews = paginator.get_page(page)

    # Форма для добавления отзыва
    review_form = ReviewForm()

    # Похожие товары (до 15, кроме текущего)
    similar_products = get_cached_similar_products(product)
    context = {
        'product': product,
        'reviews': reviews,
        'review_form': review_form,
        'average_rating': product.get_average_rating(),
        'reviews_count': product.get_reviews_count(),
        'similar_products': similar_products,
    }
    return render(request, 'bags/product_detail.html', context)


@login_required
def add_to_cart(request, product_id):
    """
    Добавление товара в корзину
    """
    product = get_object_or_404(Product, id=product_id, in_stock=True)

    # Ограничиваем количество корзин пользователя (максимум 1)
    deleted_carts = limit_user_carts(request.user, max_carts=1)

    # Получаем или создаем активный заказ
    active_order, created = Order.objects.get_or_create(
        user=request.user,
        status='new',
        defaults={
            'total_price': Decimal('0.00'),
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
    )

    # Создаем новый элемент заказа (каждый товар как отдельная позиция)
    OrderItem.objects.create(
        order=active_order,
        product=product,
        price=product.price,
        quantity=1
    )

    # Обновляем общую стоимость заказа
    active_order.total_price = sum(
        item.price * item.quantity for item in active_order.orderitem_set.all()
    )
    active_order.save()

    messages.success(request, f'Товар "{product.name}" добавлен в корзину')
    return redirect('bags:cart')


@login_required
def remove_from_cart(request, item_id):
    """
    Удаление товара из корзины
    """
    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = order_item.order

    order_item.delete()

    # Обновляем общую стоимость заказа
    order.total_price = sum(
        item.price * item.quantity for item in order.orderitem_set.all()
    )
    order.save()

    messages.success(request, 'Товар удален из корзины')
    return redirect('bags:cart')


@login_required
def cart(request):
    """
    Страница корзины пользователя
    """
    active_order = Order.objects.filter(user=request.user, status='new').first()
    return render(request, 'bags/cart.html', {
        'order': active_order
    })


@login_required
@transaction.atomic
def checkout(request):
    """
    Страница оформления заказа
    """
    active_order = Order.objects.filter(user=request.user, status='new').first()

    if not active_order or not active_order.orderitem_set.exists():
        messages.warning(request, 'Ваша корзина пуста')
        return redirect('bags:cart')

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=active_order)
        if form.is_valid():
            order = form.save(commit=False)
            order.status = 'pending'
            order.save()
            # Отправка email о новом заказе
            order_items = order.orderitem_set.all()
            items_text = '\n'.join([
                f"- {item.product.name}: {item.price} руб." for item in order_items
            ])
            # HTML-таблица товаров
            items_html = ''.join([
                f"<tr>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>{item.product.name}</td>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:center;'>1</td>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;'>{item.price} руб.</td>"
                f"</tr>" for item in order_items
            ])
            subject = f"Новый заказ #{order.id} от {order.first_name} {order.last_name}"
            message = f"""
Поступил новый заказ!\n\nДанные заказчика:\nИмя: {order.first_name}\nФамилия: {order.last_name}\nEmail: {order.email}\nТелефон: {order.phone}\n\nАдрес доставки:\n{order.address}, {order.city}, {order.postal_code}\n\nКомментарий: {order.comment or '-'}\n\nТовары:\n{items_text}\n\nСумма заказа: {order.total_price} руб.\n\nСтатус: {order.get_status_display()}\n"""
            html_message = f"""
<html>
  <body style='font-family:Arial,sans-serif;background:#f8f9fa;padding:0;margin:0;'>
    <div style='max-width:600px;margin:30px auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.07);overflow:hidden;'>
      <div style='background:linear-gradient(90deg,#6c5ce7,#a8a4e6);color:#fff;padding:24px 32px 16px 32px;'>
        <h2 style='margin:0 0 8px 0;font-weight:700;'>Новый заказ #{order.id}</h2>
        <div style='font-size:1.1rem;'>от {order.first_name} {order.last_name}</div>
      </div>
      <div style='padding:24px 32px;'>
        <h3 style='margin-top:0;color:#6c5ce7;'>Данные заказчика</h3>
        <p style='margin:0 0 8px 0;'><b>Имя:</b> {order.first_name}<br><b>Фамилия:</b> {order.last_name}<br><b>Email:</b> {order.email}<br><b>Телефон:</b> {order.phone}</p>
        <h3 style='color:#6c5ce7;'>Адрес доставки</h3>
        <p style='margin:0 0 8px 0;'>{order.address}, {order.city}, {order.postal_code}</p>
        <h3 style='color:#6c5ce7;'>Комментарий</h3>
        <p style='margin:0 0 8px 0;'>{order.comment or '-'}</p>
        <h3 style='color:#6c5ce7;'>Товары</h3>
        <table style='width:100%;border-collapse:collapse;background:#fafbfc;'>
          <thead>
            <tr style='background:#f3f0fa;'>
              <th style='padding:10px 12px;text-align:left;'>Товар</th>
              <th style='padding:10px 12px;text-align:center;'>Кол-во</th>
              <th style='padding:10px 12px;text-align:right;'>Цена</th>
            </tr>
          </thead>
          <tbody>
            {items_html}
          </tbody>
        </table>
        <div style='margin-top:18px;font-size:1.2rem;font-weight:600;text-align:right;'>
          <span style='color:#6c5ce7;'>Сумма заказа: {order.total_price} руб.</span>
        </div>
        <div style='margin-top:10px;text-align:right;'>
          <span style='display:inline-block;padding:6px 18px;border-radius:20px;background:#e3f2fd;color:#1976d2;font-weight:500;font-size:1rem;'>Статус: {order.get_status_display()}</span>
        </div>
      </div>
    </div>
  </body>
</html>
"""
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
                html_message=html_message,
            )
            # Удаляем сохраненные данные формы из сессии
            if 'order_form_data' in request.session:
                del request.session['order_form_data']
            return redirect('bags:order_submitted')
    else:
        if 'order_form_data' in request.session:
            form = OrderForm(request.session['order_form_data'], instance=active_order)
        else:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            form = OrderForm(instance=active_order, initial=initial_data)

    return render(request, 'bags/checkout.html', {
        'form': form,
        'order': active_order
    })


@login_required
def payment(request, order_id):
    """
    Страница оплаты заказа
    """
    order = get_object_or_404(Order, id=order_id, user=request.user, status='new')
    return render(request, 'bags/payment.html', {
        'order': order
    })


@login_required
@transaction.atomic
def process_payment(request, order_id):
    """
    Обработка подтверждения оплаты
    """
    order = get_object_or_404(Order, id=order_id, user=request.user, status='pending')

    if request.method == 'POST' and request.POST.get('payment_confirmation'):
        # Меняем статус заказа на 'paid'
        order.status = 'paid'
        order.save()
        # Удаляем сохраненные данные формы из сессии
        if 'order_form_data' in request.session:
            del request.session['order_form_data']
        messages.success(request, 'Заказ успешно оплачен и оформлен')
        return redirect('bags:order_history')

    messages.error(request, 'Необходимо подтвердить оплату')
    return redirect('bags:payment', order_id=order.id)


@login_required
def order_history(request):
    """
    Страница с историей заказов пользователя
    """
    # Исключаем заказы со статусом 'new' (корзина)
    orders = Order.objects.filter(
        user=request.user
    ).exclude(
        status='new'
    ).order_by('-created_at')

    return render(request, 'bags/order_history.html', {
        'orders': orders
    })


@login_required
def edit_order(request, order_id):
    """
    Редактирование заказа
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Разрешаем редактирование только заказов в статусе 'pending' или 'paid'
    if order.status not in ['pending', 'paid']:
        messages.error(request, 'Этот заказ нельзя редактировать')
        return redirect('bags:order_history')

    if request.method == 'POST':
        # Сохраняем старые данные ДО создания формы
        old_data = {
            'first_name': order.first_name,
            'last_name': order.last_name,
            'email': order.email,
            'phone': order.phone,
            'address': order.address,
            'city': order.city,
            'postal_code': order.postal_code,
            'comment': order.comment or '',
        }
        
        form = EditOrderForm(request.POST, instance=order)
        if form.is_valid():
            old_status = order.status
            
            # Сохраняем заказ с новыми данными
            order = form.save(commit=False)
            order.save()

            # Определяем что изменилось
            changes = []
            new_data = {
                'first_name': order.first_name,
                'last_name': order.last_name,
                'email': order.email,
                'phone': order.phone,
                'address': order.address,
                'city': order.city,
                'postal_code': order.postal_code,
                'comment': order.comment or '',
            }
            
            field_names = {
                'first_name': 'Имя',
                'last_name': 'Фамилия',
                'email': 'Email',
                'phone': 'Телефон',
                'address': 'Адрес',
                'city': 'Город',
                'postal_code': 'Почтовый индекс',
                'comment': 'Комментарий',
            }
            
            # Отладочная информация
            print(f"DEBUG: Сравнение данных для заказа #{order.id}")
            print(f"DEBUG: Старые данные: {old_data}")
            print(f"DEBUG: Новые данные: {new_data}")
            
            for field, old_value in old_data.items():
                new_value = new_data[field]
                if old_value != new_value:
                    changes.append(f"{field_names[field]}: '{old_value}' → '{new_value}'")
                    print(f"DEBUG: Найдено изменение в поле {field}: '{old_value}' → '{new_value}'")
                else:
                    print(f"DEBUG: Поле {field} не изменилось: '{old_value}'")
            
            print(f"DEBUG: Всего изменений: {len(changes)}")
            print(f"DEBUG: Список изменений: {changes}")

            # Отправляем уведомление об изменении заказа администратору
            try:
                subject = f"Заказ #{order.id} изменен"
                message = f"""
Заказ #{order.id} был изменен пользователем {order.first_name} {order.last_name}.

Новые данные заказчика:
Имя: {order.first_name}
Фамилия: {order.last_name}
Email: {order.email}
Телефон: {order.phone}

Новый адрес доставки:
{order.address}, {order.city}, {order.postal_code}

Комментарий: {order.comment or '-'}

Статус заказа: {order.get_status_display()}

Изменения:
{chr(10).join(changes) if changes else 'Изменений не обнаружено'}
"""
                # HTML-версия для администратора
                changes_html = '<br>'.join([f"• {change}" for change in changes]) if changes else 'Изменений не обнаружено'
                html_message = f"""
<html>
  <body style='font-family:Arial,sans-serif;background:#f8f9fa;padding:0;margin:0;'>
    <div style='max-width:600px;margin:30px auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.07);overflow:hidden;'>
      <div style='background:linear-gradient(90deg,#ff9800,#ffb74d);color:#fff;padding:24px 32px 16px 32px;'>
        <h2 style='margin:0 0 8px 0;font-weight:700;'>Заказ #{order.id} изменен</h2>
        <div style='font-size:1.1rem;'>пользователем {order.first_name} {order.last_name}</div>
      </div>
      <div style='padding:24px 32px;'>
        <h3 style='margin-top:0;color:#ff9800;'>Новые данные заказчика</h3>
        <p style='margin:0 0 8px 0;'><b>Имя:</b> {order.first_name}<br><b>Фамилия:</b> {order.last_name}<br><b>Email:</b> {order.email}<br><b>Телефон:</b> {order.phone}</p>
        <h3 style='color:#ff9800;'>Новый адрес доставки</h3>
        <p style='margin:0 0 8px 0;'>{order.address}, {order.city}, {order.postal_code}</p>
        <h3 style='color:#ff9800;'>Комментарий</h3>
        <p style='margin:0 0 8px 0;'>{order.comment or '-'}</p>
        <h3 style='color:#ff9800;'>Изменения</h3>
        <div style='background:#fff3e0;padding:12px;border-radius:8px;margin-bottom:16px;'>
          <p style='margin:0;color:#f57c00;'>{changes_html}</p>
        </div>
        <div style='margin-top:18px;text-align:right;'>
          <span style='display:inline-block;padding:6px 18px;border-radius:20px;background:#fff3e0;color:#f57c00;font-weight:500;font-size:1rem;'>Статус: {order.get_status_display()}</span>
        </div>
      </div>
    </div>
  </body>
</html>
"""
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,  # Не прерываем процесс если email не отправился
                    html_message=html_message,
                )
            except Exception as e:
                # Логируем ошибку, но не прерываем процесс
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка отправки email администратору при редактировании заказа {order.id}: {e}')

            # Отправляем уведомление пользователю
            try:
                user_subject = f"Заказ #{order.id} обновлен"
                user_message = f"""
Уважаемый(ая) {order.first_name} {order.last_name}!

Ваш заказ #{order.id} был успешно обновлен.

Обновленные данные:
- Имя: {order.first_name}
- Фамилия: {order.last_name}
- Email: {order.email}
- Телефон: {order.phone}
- Адрес: {order.address}, {order.city}, {order.postal_code}
- Комментарий: {order.comment or '-'}

Если вы не вносили эти изменения, пожалуйста, свяжитесь с нами.

С уважением,
Команда магазина сумочек из бусин
"""
                # HTML-версия для пользователя
                user_html_message = f"""
<html>
  <body style='font-family:Arial,sans-serif;background:#f8f9fa;padding:0;margin:0;'>
    <div style='max-width:600px;margin:30px auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.07);overflow:hidden;'>
      <div style='background:linear-gradient(90deg,#4caf50,#66bb6a);color:#fff;padding:24px 32px 16px 32px;'>
        <h2 style='margin:0 0 8px 0;font-weight:700;'>Заказ #{order.id} обновлен</h2>
        <div style='font-size:1.1rem;'>Уважаемый(ая) {order.first_name} {order.last_name}!</div>
      </div>
      <div style='padding:24px 32px;'>
        <p style='margin:0 0 16px 0;font-size:1.1rem;'>Ваш заказ был успешно обновлен.</p>
        <h3 style='margin-top:0;color:#4caf50;'>Обновленные данные</h3>
        <div style='background:#f8f9fa;padding:16px;border-radius:8px;margin-bottom:16px;'>
          <p style='margin:0 0 8px 0;'><b>Имя:</b> {order.first_name}</p>
          <p style='margin:0 0 8px 0;'><b>Фамилия:</b> {order.last_name}</p>
          <p style='margin:0 0 8px 0;'><b>Email:</b> {order.email}</p>
          <p style='margin:0 0 8px 0;'><b>Телефон:</b> {order.phone}</p>
          <p style='margin:0 0 8px 0;'><b>Адрес:</b> {order.address}, {order.city}, {order.postal_code}</p>
          <p style='margin:0;'><b>Комментарий:</b> {order.comment or '-'}</p>
        </div>
        <div style='background:#fff3cd;border:1px solid #ffeaa7;border-radius:8px;padding:16px;margin-top:16px;'>
          <p style='margin:0;color:#856404;font-size:0.9rem;'><i>Если вы не вносили эти изменения, пожалуйста, свяжитесь с нами.</i></p>
        </div>
        <div style='margin-top:24px;padding-top:16px;border-top:1px solid #e9ecef;text-align:center;color:#6c757d;font-size:0.9rem;'>
          <p style='margin:0;'>С уважением,<br>Команда магазина сумочек из бусин</p>
        </div>
      </div>
    </div>
  </body>
</html>
"""
                send_mail(
                    subject=user_subject,
                    message=user_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[order.email],
                    fail_silently=True,  # Не прерываем процесс если email не отправился
                    html_message=user_html_message,
                )
            except Exception as e:
                # Логируем ошибку, но не прерываем процесс
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка отправки email пользователю при редактировании заказа {order.id}: {e}')

            # Показываем сообщение об успехе с информацией об изменениях
            if changes:
                changes_text = ', '.join(changes[:3])  # Показываем первые 3 изменения
                if len(changes) > 3:
                    changes_text += f' и еще {len(changes) - 3}'
                messages.success(request, f'Заказ успешно обновлен. Изменения: {changes_text}')
            else:
                messages.info(request, 'Заказ сохранен без изменений')

            # Перенаправляем на страницу истории заказов с якорем на этот заказ
            return redirect('bags:order_history')
        else:
            # Показываем ошибки валидации формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Ошибка в поле "{field}": {error}')
    else:
        form = EditOrderForm(instance=order)

    return render(request, 'bags/edit_order.html', {
        'form': form,
        'order': order
    })


@login_required
def cancel_order(request, order_id):
    """
    Отмена заказа
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Разрешаем отмену только заказов в статусе 'pending' или 'paid'
    if order.status not in ['pending', 'paid']:
        messages.error(request, 'Этот заказ нельзя отменить')
        return redirect('bags:order_history')

    if request.method == 'POST':
        # Меняем статус на 'cancelled'
        old_status = order.status
        order.status = 'cancelled'
        order.save()

        # Отправляем уведомление об отмене заказа
        subject = f"Заказ #{order.id} отменен"
        message = f"""
Заказ #{order.id} был отменен пользователем {order.first_name} {order.last_name}.

Данные заказчика:
Имя: {order.first_name}
Фамилия: {order.last_name}
Email: {order.email}
Телефон: {order.phone}

Адрес доставки:
{order.address}, {order.city}, {order.postal_code}

Комментарий: {order.comment or '-'}

Предыдущий статус: {dict(Order.STATUS_CHOICES)[old_status]}
Новый статус: Отменен
"""
        # HTML-версия для администратора
        html_message = f"""
<html>
  <body style='font-family:Arial,sans-serif;background:#f8f9fa;padding:0;margin:0;'>
    <div style='max-width:600px;margin:30px auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.07);overflow:hidden;'>
      <div style='background:linear-gradient(90deg,#f44336,#ef5350);color:#fff;padding:24px 32px 16px 32px;'>
        <h2 style='margin:0 0 8px 0;font-weight:700;'>Заказ #{order.id} отменен</h2>
        <div style='font-size:1.1rem;'>пользователем {order.first_name} {order.last_name}</div>
      </div>
      <div style='padding:24px 32px;'>
        <h3 style='margin-top:0;color:#f44336;'>Данные заказчика</h3>
        <p style='margin:0 0 8px 0;'><b>Имя:</b> {order.first_name}<br><b>Фамилия:</b> {order.last_name}<br><b>Email:</b> {order.email}<br><b>Телефон:</b> {order.phone}</p>
        <h3 style='color:#f44336;'>Адрес доставки</h3>
        <p style='margin:0 0 8px 0;'>{order.address}, {order.city}, {order.postal_code}</p>
        <h3 style='color:#f44336;'>Комментарий</h3>
        <p style='margin:0 0 8px 0;'>{order.comment or '-'}</p>
        <div style='margin-top:18px;display:flex;justify-content:space-between;align-items:center;'>
          <span style='display:inline-block;padding:6px 18px;border-radius:20px;background:#ffebee;color:#d32f2f;font-weight:500;font-size:1rem;'>Предыдущий статус: {dict(Order.STATUS_CHOICES)[old_status]}</span>
          <span style='display:inline-block;padding:6px 18px;border-radius:20px;background:#ffebee;color:#d32f2f;font-weight:500;font-size:1rem;'>Новый статус: Отменен</span>
        </div>
      </div>
    </div>
  </body>
</html>
"""
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
            html_message=html_message,
        )

        # Отправляем уведомление пользователю
        user_subject = f"Заказ #{order.id} отменен"
        user_message = f"""
Уважаемый(ая) {order.first_name} {order.last_name}!

Ваш заказ #{order.id} был успешно отменен.

Детали заказа:
- Дата создания: {order.created_at.strftime('%d.%m.%Y %H:%M')}
- Сумма заказа: {order.total_price} ₽
- Статус: Отменен

Если у вас есть вопросы, пожалуйста, свяжитесь с нами.

С уважением,
Команда магазина сумочек из бусин
"""
        # HTML-версия для пользователя
        user_html_message = f"""
<html>
  <body style='font-family:Arial,sans-serif;background:#f8f9fa;padding:0;margin:0;'>
    <div style='max-width:600px;margin:30px auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.07);overflow:hidden;'>
      <div style='background:linear-gradient(90deg,#f44336,#ef5350);color:#fff;padding:24px 32px 16px 32px;'>
        <h2 style='margin:0 0 8px 0;font-weight:700;'>Заказ #{order.id} отменен</h2>
        <div style='font-size:1.1rem;'>Уважаемый(ая) {order.first_name} {order.last_name}!</div>
      </div>
      <div style='padding:24px 32px;'>
        <p style='margin:0 0 16px 0;font-size:1.1rem;'>Ваш заказ был успешно отменен.</p>
        <h3 style='margin-top:0;color:#f44336;'>Детали заказа</h3>
        <div style='background:#f8f9fa;padding:16px;border-radius:8px;margin-bottom:16px;'>
          <p style='margin:0 0 8px 0;'><b>Дата создания:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}</p>
          <p style='margin:0 0 8px 0;'><b>Сумма заказа:</b> {order.total_price} ₽</p>
          <p style='margin:0;'><b>Статус:</b> Отменен</p>
        </div>
        <div style='background:#fff3cd;border:1px solid #ffeaa7;border-radius:8px;padding:16px;margin-top:16px;'>
          <p style='margin:0;color:#856404;font-size:0.9rem;'><i>Если у вас есть вопросы, пожалуйста, свяжитесь с нами.</i></p>
        </div>
        <div style='margin-top:24px;padding-top:16px;border-top:1px solid #e9ecef;text-align:center;color:#6c757d;font-size:0.9rem;'>
          <p style='margin:0;'>С уважением,<br>Команда магазина сумочек из бусин</p>
        </div>
      </div>
    </div>
  </body>
</html>
"""
        send_mail(
            subject=user_subject,
            message=user_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
            html_message=user_html_message,
        )

        messages.success(request, 'Заказ успешно отменен')
        return redirect('bags:order_history')

    return render(request, 'bags/cancel_order_confirm.html', {
        'order': order
    })


@login_required
def favorites(request):
    """
    Страница с избранными товарами пользователя
    """
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    return render(request, 'bags/favorites.html', {
        'favorites': favorites
    })


@login_required
def add_to_favorites(request, product_id):
    """
    Добавление товара в избранное
    """
    product = get_object_or_404(Product, id=product_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

    if created:
        messages.success(request, 'Товар добавлен в избранное')
    else:
        messages.info(request, 'Товар уже в избранном')

    return redirect('bags:product_detail', slug=product.slug)


@login_required
def remove_from_favorites(request, product_id):
    """
    Удаление товара из избранного

    Args:
        product_id (int): ID товара

    Returns:
        HttpResponse: Перенаправляет на страницу избранного
    """
    product = get_object_or_404(Product, id=product_id)
    favorite = get_object_or_404(Favorite, user=request.user, product=product)
    favorite.delete()
    messages.success(request, 'Товар удален из избранного')
    return redirect('bags:favorites')


@login_required
@require_POST
def add_review(request, pk):
    """
    Добавление отзыва к товару
    """
    product = get_object_or_404(Product, id=pk)
    form = ReviewForm(request.POST)

    if form.is_valid():
        # Проверяем, не оставлял ли пользователь уже отзыв
        if Review.objects.filter(user=request.user, product=product).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Вы уже оставляли отзыв на этот товар.'
            })
        try:
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.is_approved = False  # Теперь отзыв требует модерации
            review.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Спасибо! Ваш отзыв отправлен на модерацию и появится после проверки.'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка при сохранении отзыва: {str(e)}'
            })
    return JsonResponse({
        'status': 'error',
        'message': 'Пожалуйста, исправьте ошибки в форме.',
        'errors': form.errors
    })


@login_required
@require_POST
def delete_review(request, review_id):
    """
    Удаление отзыва
    """
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product_id = review.product.id
    review.delete()
    messages.success(request, 'Отзыв успешно удален')
    return redirect('bags:product_detail', slug=review.product.slug)


@login_required
def vote_review(request, review_id):
    """
    Представление для оценки полезности отзыва
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Необходимо войти в систему'
        }, status=403)

    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Отзыв не найден'
        }, status=404)

    is_helpful = request.POST.get('is_helpful') == 'true'

    # Проверяем, не голосовал ли уже пользователь
    try:
        vote = ReviewVote.objects.get(user=request.user, review=review)
        # Если голос такой же, удаляем его
        if vote.is_helpful == is_helpful:
            vote.delete()
            action = 'removed'
        else:
            # Если голос другой, меняем его
            vote.is_helpful = is_helpful
            vote.save()
            action = 'changed'
    except ReviewVote.DoesNotExist:
        # Создаем новый голос
        ReviewVote.objects.create(
            user=request.user,
            review=review,
            is_helpful=is_helpful
        )
        action = 'added'

    return JsonResponse({
        'status': 'success',
        'action': action,
        'helpful_count': review.get_helpful_votes(),
        'unhelpful_count': review.get_unhelpful_votes()
    })


def popular_products(request):
    """
    Страница с популярными товарами
    """
    popular_products = get_cached_popular_products()

    # Пагинация
    paginator = Paginator(popular_products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    return render(request, 'bags/popular_products.html', {
        'products': products,
        'title': 'Популярные товары'
    })


def order_submitted(request):
    """
    Страница подтверждения оформления заказа
    """
    return render(request, 'bags/order_submitted.html')


def privacy_policy(request):
    """
    Страница политики конфиденциальности
    """
    return render(request, 'bags/privacy_policy.html')

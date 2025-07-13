from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator
# from django.utils.translation import gettext_lazy as _
# from django.utils import timezone
# from django.core.exceptions import ValidationError
# from django.utils.text import slugify
# from PIL import Image
# import os
import secrets


class Category(models.Model):
    """
    Модель категории товаров

    Attributes:
        name (str): Название категории
        description (str): Описание категории
        created_at (datetime): Дата создания категории
    """
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание категории")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    """
    Инвалидация кэша категорий при изменении
    """
    if settings.CACHE_ENABLED:
        cache.delete('categories')
        # Инвалидируем кэш статистики
        cache.delete('site_stats')


class Product(models.Model):
    """
    Модель товара (сумочки)

    Attributes:
        name (str): Название товара
        description (str): Описание товара
        price (decimal): Цена товара
        category (Category): Категория товара
        image (ImageField): Основное изображение товара
        in_stock (bool): Наличие товара
        created_at (datetime): Дата добавления товара
        is_popular (bool): Популярный товар
        views_count (int): Количество просмотров товара
        materials (str): Материалы, из которых изготовлен товар
        height (float): Высота товара в сантиметрах
        length (float): Длина товара в сантиметрах
        depth (float): Глубина товара в сантиметрах
        bead_color (str): Цвет бусин
        hardware_color (str): Цвет фурнитуры
        slug (str): Уникальный слаг для товара
    """
    name = models.CharField(max_length=200, verbose_name="Название товара")
    description = models.TextField(verbose_name="Описание товара")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категория")
    image = models.ImageField(upload_to='products/', verbose_name="Основное изображение")
    in_stock = models.BooleanField(default=True, verbose_name="В наличии")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    is_popular = models.BooleanField(default=False, verbose_name="Популярный товар")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Количество просмотров")
    materials = models.TextField(verbose_name="Материалы", blank=True)
    height = models.FloatField(verbose_name="Высота (см)", null=True, blank=True)
    length = models.FloatField(verbose_name="Длина (см)", null=True, blank=True)
    depth = models.FloatField(verbose_name="Глубина (см)", null=True, blank=True)
    bead_color = models.CharField(max_length=100, verbose_name="Цвет бусин", blank=True)
    hardware_color = models.CharField(max_length=100, verbose_name="Цвет фурнитуры", blank=True)
    slug = models.SlugField(blank=True, max_length=20)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_average_rating(self):
        """Получение средней оценки товара"""
        reviews = self.review_set.filter(is_approved=True)
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)

    def get_reviews_count(self):
        """Получение количества отзывов"""
        return self.review_set.filter(is_approved=True).count()

    def get_rating_distribution(self):
        """
        Получение распределения оценок товара
        Returns:
            dict: Словарь с процентами отзывов для каждой оценки
        """
        reviews = self.review_set.filter(is_approved=True)
        if not reviews:
            return {i: 0 for i in range(1, 6)}

        total_reviews = reviews.count()
        distribution = {}

        for rating in range(1, 6):
            rating_count = reviews.filter(rating=rating).count()
            distribution[rating] = (rating_count / total_reviews) * 100

        return distribution

    def get_rating_percentage(self):
        """
        Получение процента отзывов для каждой оценки
        Returns:
            dict: Словарь с процентами отзывов для каждой оценки (1-5)
        """
        reviews = self.review_set.filter(is_approved=True)
        if not reviews:
            return {i: 0 for i in range(1, 6)}

        total_reviews = reviews.count()
        distribution = {}

        for rating in range(1, 6):
            rating_reviews = reviews.filter(rating=rating).count()
            distribution[rating] = (rating_reviews / total_reviews) * 100

        return distribution

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = secrets.token_urlsafe(8).replace('-', '').replace('_', '')[:12]
        super().save(*args, **kwargs)


@receiver([post_save, post_delete], sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    """
    Инвалидация кэша товара при изменении
    """
    if settings.CACHE_ENABLED:
        cache.delete(f'product_{instance.id}')
        # Инвалидируем кэш фильтров
        cache.delete('filter_data')
        # Инвалидируем кэш популярных товаров
        cache.delete('popular_products')
        # Инвалидируем кэш последних товаров
        cache.delete('latest_products_8')
        # Инвалидируем кэш статистики
        cache.delete('site_stats')
        # Инвалидируем кэш похожих товаров для всех товаров этой категории
        for product in Product.objects.filter(category=instance.category):
            cache.delete(f'similar_products_{product.id}_15')


class ProductImage(models.Model):
    """
    Модель дополнительных изображений товара

    Attributes:
        product (Product): Товар, к которому относится изображение
        image (ImageField): Изображение товара
        order (int): Порядок отображения изображения
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="Товар")
    image = models.ImageField(upload_to='products/additional/', verbose_name="Изображение")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок отображения")

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ['order']

    def __str__(self):
        return f"Изображение {self.order} для {self.product.name}"


class Order(models.Model):
    """
    Модель заказа

    Attributes:
        user (User): Пользователь, сделавший заказ
        products (Product): Товары в заказе
        total_price (decimal): Общая стоимость заказа
        status (str): Статус заказа
        created_at (datetime): Дата создания заказа
        updated_at (datetime): Дата обновления заказа
        first_name (str): Имя заказчика
        last_name (str): Фамилия заказчика
        email (str): Email заказчика
        phone (str): Телефон заказчика
        address (str): Адрес доставки
        city (str): Город доставки
        postal_code (str): Почтовый индекс
        comment (str): Комментарий к заказу
    """
    STATUS_CHOICES = [
        ('new', 'Корзина'),
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь")
    products = models.ManyToManyField(Product, through='OrderItem', verbose_name="Товары")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая стоимость")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    # Информация о заказчике
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Телефон")

    # Информация о доставке
    address = models.TextField(verbose_name="Адрес доставки")
    city = models.CharField(max_length=100, verbose_name="Город")
    postal_code = models.CharField(max_length=20, verbose_name="Почтовый индекс")

    # Дополнительная информация
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий к заказу")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),  # Для поиска корзины пользователя
            models.Index(fields=['status', 'created_at']),  # Для очистки старых корзин
            models.Index(fields=['user', 'status', 'created_at']),  # Композитный индекс
        ]

    def __str__(self):
        return f"Заказ #{self.id} от {self.user.username}"


class OrderItem(models.Model):
    """
    Модель элемента заказа

    Attributes:
        order (Order): Заказ
        product (Product): Товар
        quantity (int): Количество товара
        price (decimal): Цена товара на момент заказа
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")

    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"
        indexes = [
            models.Index(fields=['order', 'product']),  # Для поиска товаров в заказе
            models.Index(fields=['order']),  # Для получения всех товаров заказа
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Favorite(models.Model):
    """
    Модель избранных товаров пользователя

    Attributes:
        user (User): Пользователь
        product (Product): Товар
        created_at (datetime): Дата добавления в избранное
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Избранный товар"
        verbose_name_plural = "Избранные товары"
        unique_together = ('user', 'product')  # Предотвращает дублирование

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class Review(models.Model):
    """
    Модель отзыва о товаре

    Attributes:
        user (User): Пользователь, оставивший отзыв
        product (Product): Товар, к которому относится отзыв
        rating (int): Оценка товара (от 1 до 5)
        text (str): Текст отзыва
        created_at (datetime): Дата создания отзыва
        updated_at (datetime): Дата обновления отзыва
        is_approved (bool): Одобрен ли отзыв модератором
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Оценка"
    )
    text = models.TextField(verbose_name="Текст отзыва")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']
        unique_together = ('user', 'product')  # Один отзыв от пользователя на товар

    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.rating})"

    def save(self, *args, **kwargs):
        # Автоматически одобряем отзывы от администраторов
        if self.user.is_staff or self.user.is_superuser:
            self.is_approved = True
        super().save(*args, **kwargs)

    def get_helpful_votes(self):
        """Получение количества голосов 'полезно'"""
        return self.reviewvote_set.filter(is_helpful=True).count()

    def get_unhelpful_votes(self):
        """Получение количества голосов 'не полезно'"""
        return self.reviewvote_set.filter(is_helpful=False).count()

    def get_user_vote(self, user):
        """Получение голоса пользователя"""
        if user.is_authenticated:
            try:
                vote = self.reviewvote_set.get(user=user)
                return vote.is_helpful
            except ReviewVote.DoesNotExist:
                return None
        return None


@receiver([post_save, post_delete], sender=Review)
def invalidate_product_cache(sender, instance, **kwargs):
    """
    Инвалидация кэша товара при изменении отзывов
    """
    if settings.CACHE_ENABLED:
        cache.delete(f'product_{instance.product.id}')


class ReviewVote(models.Model):
    """
    Модель оценки полезности отзыва

    Attributes:
        user (User): Пользователь, оценивший отзыв
        review (Review): Отзыв
        is_helpful (bool): Полезен ли отзыв
        created_at (datetime): Дата оценки
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь")
    review = models.ForeignKey(Review, on_delete=models.CASCADE, verbose_name="Отзыв")
    is_helpful = models.BooleanField(verbose_name="Полезен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата оценки")

    class Meta:
        verbose_name = "Оценка отзыва"
        verbose_name_plural = "Оценки отзывов"
        unique_together = ('user', 'review')  # Один голос от пользователя на отзыв

    def __str__(self):
        return f"{self.user.email} - {'Полезно' if self.is_helpful else 'Не полезно'}"

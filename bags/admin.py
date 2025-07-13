from django.contrib import admin
from .models import Category, Product, Order, OrderItem, Favorite, Review, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Category
    """
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    ordering = ('name',)


class OrderItemInline(admin.TabularInline):
    """
    Встроенная форма для элементов заказа в административной панели
    """
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')


class ProductImageInline(admin.TabularInline):
    """
    Встроенная форма для дополнительных изображений товара
    """
    model = ProductImage
    extra = 1
    fields = ('image', 'order')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Order
    """
    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'total_price', 'created_at')
        }),
        ('Информация о доставке', {
            'fields': ('address', 'city', 'postal_code')
        }),
        ('Контактная информация', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Дополнительно', {
            'fields': ('comment',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Административная панель для модели OrderItem
    """
    list_display = ('order', 'product', 'quantity', 'price')
    list_filter = ('order__status',)
    search_fields = ('order__user__email', 'product__name')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Product
    """
    list_display = ('name', 'category', 'price', 'in_stock', 'created_at')
    list_filter = ('category', 'in_stock', 'created_at')
    search_fields = ('name', 'description', 'materials', 'bead_color', 'hardware_color')
    list_editable = ('price', 'in_stock')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    inlines = [ProductImageInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'description', 'price', 'in_stock', 'image')
        }),
        ('Характеристики', {
            'fields': ('materials', 'bead_color', 'hardware_color', 'height', 'length', 'depth')
        }),
        ('Дополнительно', {
            'fields': ('is_popular', 'views_count', 'created_at')
        }),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__email', 'product__name')
    ordering = ('-created_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Административная панель для модели Review
    """
    list_display = ('user', 'product', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('user__email', 'product__name', 'text')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Одобрить выбранные отзывы"

    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    reject_reviews.short_description = "Отклонить выбранные отзывы"

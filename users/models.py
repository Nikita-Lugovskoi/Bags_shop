from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

# не всегда так можно делать
NULLABLE = {'blank': True, 'null': True}


class User(AbstractUser):
    """
    Модель пользователя
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Администратор')
        USER = 'USER', _('Пользователь')

    username = None
    email = models.EmailField(unique=True, verbose_name='Email')
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER, verbose_name='Роль')
    is_verified = models.BooleanField(default=False, verbose_name='Подтвержден')
    verification_code = models.CharField(max_length=50, blank=True, null=True, verbose_name='Код подтверждения')
    verification_code_created_at = models.DateTimeField(blank=True, null=True, verbose_name='Время создания кода')
    new_email = models.EmailField(blank=True, null=True, verbose_name='Новый email')
    email_verification_token = models.CharField(max_length=50, blank=True, null=True, verbose_name='Токен подтверждения email')
    new_password = models.CharField(max_length=128, blank=True, null=True, verbose_name='Новый пароль (зашифрованный)')
    password_verification_token = models.CharField(max_length=50, blank=True, null=True, verbose_name='Токен подтверждения пароля')
    avatar = models.ImageField(
        upload_to='users/avatars/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        verbose_name='Аватар'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def get_orders_count(self):
        """
        Получение количества активных заказов пользователя
        (заказы со статусами 'processing', 'shipped', 'delivered')
        Исключаются заказы со статусом 'new' (корзина) и 'cancelled' (отмененные)
        """
        return self.order_set.exclude(status__in=['new', 'cancelled']).count()

    def get_favorites_count(self):
        return self.favorite_set.count()

    def get_reviews_count(self):
        return self.review_set.count()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['id']

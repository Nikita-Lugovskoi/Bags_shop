from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import Order, OrderItem
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def cleanup_old_carts(days=30, dry_run=False):
    """
    Автоматическая очистка старых корзин

    Args:
        days (int): Количество дней, после которых корзины считаются старыми
        dry_run (bool): Если True, только показывает что будет удалено

    Returns:
        dict: Статистика очистки
    """
    cutoff_date = timezone.now() - timedelta(days=days)

    # Находим старые корзины
    old_carts = Order.objects.filter(
        status='new',
        created_at__lt=cutoff_date
    )

    old_carts_count = old_carts.count()

    if old_carts_count == 0:
        return {
            'deleted_carts': 0,
            'deleted_items': 0,
            'message': f'Старых корзин (старше {days} дней) не найдено.'
        }

    # Подсчитываем количество элементов заказов
    total_items = OrderItem.objects.filter(
        order__in=old_carts
    ).count()

    if dry_run:
        return {
            'deleted_carts': 0,
            'deleted_items': 0,
            'message': f'Найдено {old_carts_count} старых корзин с {total_items} товарами (режим предварительного просмотра)'
        }

    # Выполняем удаление
    try:
        with transaction.atomic():
            # Сначала удаляем элементы заказов
            deleted_items = OrderItem.objects.filter(
                order__in=old_carts
            ).delete()

            # Затем удаляем сами заказы
            deleted_carts = old_carts.delete()

            logger.info(
                f'Автоматическая очистка корзин: удалено {deleted_carts[0]} корзин '
                f'с {deleted_items[0]} товарами (старше {days} дней)'
            )

            return {
                'deleted_carts': deleted_carts[0],
                'deleted_items': deleted_items[0],
                'message': f'Успешно удалено {deleted_carts[0]} корзин с {deleted_items[0]} товарами'
            }

    except Exception as e:
        logger.error(f'Ошибка при автоматической очистке корзин: {e}')
        return {
            'deleted_carts': 0,
            'deleted_items': 0,
            'error': str(e),
            'message': f'Ошибка при удалении: {e}'
        }


def get_cart_statistics():
    """
    Получение статистики корзин

    Returns:
        dict: Статистика корзин
    """
    total_carts = Order.objects.filter(status='new').count()
    total_cart_items = OrderItem.objects.filter(order__status='new').count()

    # Старые корзины (старше 7 дней)
    old_carts = Order.objects.filter(
        status='new',
        created_at__lt=timezone.now() - timedelta(days=7)
    ).count()

    # Старые корзины (старше 30 дней)
    very_old_carts = Order.objects.filter(
        status='new',
        created_at__lt=timezone.now() - timedelta(days=30)
    ).count()

    return {
        'total_carts': total_carts,
        'total_cart_items': total_cart_items,
        'old_carts_7_days': old_carts,
        'old_carts_30_days': very_old_carts,
        'needs_cleanup': very_old_carts > 0
    }


def limit_user_carts(user, max_carts=1):
    """
    Ограничивает количество корзин пользователя

    Args:
        user: Пользователь
        max_carts (int): Максимальное количество корзин

    Returns:
        int: Количество удаленных корзин
    """
    user_carts = Order.objects.filter(
        user=user,
        status='new'
    ).order_by('-created_at')

    if user_carts.count() <= max_carts:
        return 0

    # Удаляем старые корзины, оставляя только самые новые
    carts_to_delete = user_carts[max_carts:]

    try:
        with transaction.atomic():
            # Удаляем элементы заказов
            OrderItem.objects.filter(
                order__in=carts_to_delete
            ).delete()

            # Удаляем корзины
            deleted_count = carts_to_delete.delete()[0]

            logger.info(
                f'Ограничение корзин пользователя {user.email}: '
                f'удалено {deleted_count} старых корзин'
            )

            return deleted_count

    except Exception as e:
        logger.error(f'Ошибка при ограничении корзин пользователя {user.email}: {e}')
        return 0


def send_cleanup_notification(stats, threshold_days=30):
    """
    Отправляет уведомление администратору о необходимости очистки корзин

    Args:
        stats (dict): Статистика корзин
        threshold_days (int): Пороговое количество дней для уведомления

    Returns:
        bool: True если уведомление отправлено, False если не нужно
    """
    # Проверяем, нужно ли отправлять уведомление
    if stats['old_carts_30_days'] == 0:
        return False

    # Определяем уровень критичности
    if stats['old_carts_30_days'] > 100:
        severity = "КРИТИЧЕСКИЙ"
        color_gradient = "linear-gradient(90deg,#f44336,#ef5350)"
        status_color = "#d32f2f"
    elif stats['old_carts_30_days'] > 50:
        severity = "ВЫСОКИЙ"
        color_gradient = "linear-gradient(90deg,#ff9800,#ffb74d)"
        status_color = "#f57c00"
    else:
        severity = "СРЕДНИЙ"
        color_gradient = "linear-gradient(90deg,#ffc107,#ffd54f)"
        status_color = "#f57f17"

    subject = f"⚠️ Требуется очистка корзин - {severity} уровень"

    # Текстовое сообщение
    message = f"""
ТРЕБУЕТСЯ ОЧИСТКА КОРЗИН!

Статистика корзин:
- Всего корзин: {stats['total_carts']}
- Товаров в корзинах: {stats['total_cart_items']}
- Старых корзин (>7 дней): {stats['old_carts_7_days']}
- Старых корзин (>30 дней): {stats['old_carts_30_days']}

Рекомендуемые действия:
1. Запустить очистку: python manage.py cleanup_old_carts --days 30 --force
2. Проверить статистику: python manage.py cart_stats --days 30
3. Настроить автоматическую очистку

Уровень критичности: {severity}
"""

    # HTML-версия
    html_message = f"""
<html>
  <body style='font-family:Arial,sans-serif;background:#f8f9fa;padding:0;margin:0;'>
    <div style='max-width:600px;margin:30px auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.07);overflow:hidden;'>
      <div style='background:{color_gradient};color:#fff;padding:24px 32px 16px 32px;'>
        <h2 style='margin:0 0 8px 0;font-weight:700;'>⚠️ Требуется очистка корзин</h2>
        <div style='font-size:1.1rem;'>Уровень критичности: {severity}</div>
      </div>
      <div style='padding:24px 32px;'>
        <h3 style='margin-top:0;color:{status_color};'>📊 Статистика корзин</h3>
        <div style='background:#f8f9fa;padding:16px;border-radius:8px;margin-bottom:16px;'>
          <p style='margin:0 0 8px 0;'><b>Всего корзин:</b> {stats['total_carts']}</p>
          <p style='margin:0 0 8px 0;'><b>Товаров в корзинах:</b> {stats['total_cart_items']}</p>
          <p style='margin:0 0 8px 0;'><b>Старых корзин (>7 дней):</b> {stats['old_carts_7_days']}</p>
          <p style='margin:0;'><b>Старых корзин (>30 дней):</b> {stats['old_carts_30_days']}</p>
        </div>

        <h3 style='color:{status_color};'>🔧 Рекомендуемые действия</h3>
        <div style='background:#fff3cd;border:1px solid #ffeaa7;border-radius:8px;padding:16px;margin-bottom:16px;'>
          <p style='margin:0 0 8px 0;'><b>1.</b> Запустить очистку:</p>
          <code style='background:#f8f9fa;padding:4px 8px;border-radius:4px;font-family:monospace;'>python manage.py cleanup_old_carts --days 30 --force</code>

          <p style='margin:16px 0 8px 0;'><b>2.</b> Проверить статистику:</p>
          <code style='background:#f8f9fa;padding:4px 8px;border-radius:4px;font-family:monospace;'>python manage.py cart_stats --days 30</code>

          <p style='margin:16px 0 8px 0;'><b>3.</b> Настроить автоматическую очистку</p>
        </div>

        <div style='background:#e3f2fd;border:1px solid #bbdefb;border-radius:8px;padding:16px;margin-top:16px;'>
          <p style='margin:0;color:#1976d2;font-size:0.9rem;'><i>💡 Совет: Настройте автоматическую очистку через cron или планировщик задач для предотвращения накопления старых корзин.</i></p>
        </div>

        <div style='margin-top:24px;padding-top:16px;border-top:1px solid #e9ecef;text-align:center;color:#6c757d;font-size:0.9rem;'>
          <p style='margin:0;'>Это автоматическое уведомление от системы управления корзинами</p>
        </div>
      </div>
    </div>
  </body>
</html>
"""

    try:
        # Проверяем настройки email
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            logger.warning(
                'Email не настроен. Уведомление о очистке корзин не отправлено. '
                f'Старых корзин: {stats["old_carts_30_days"]}'
            )
            # В тестовой среде просто логируем уведомление
            print("\n📧 УВЕДОМЛЕНИЕ (email не настроен):")
            print(f"Тема: {subject}")
            print(f"Старых корзин: {stats['old_carts_30_days']}")
            print(f"Уровень критичности: {severity}")
            return True

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
            html_message=html_message,
        )

        logger.info(
            'Отправлено уведомление о необходимости очистки корзин. '
            f'Старых корзин: {stats["old_carts_30_days"]}'
        )

        return True

    except Exception as e:
        logger.error(f'Ошибка при отправке уведомления о очистке корзин: {e}')
        # В случае ошибки также показываем уведомление в консоли
        print("\n📧 УВЕДОМЛЕНИЕ (ошибка email):")
        print(f"Тема: {subject}")
        print(f"Старых корзин: {stats['old_carts_30_days']}")
        print(f"Уровень критичности: {severity}")
        return False

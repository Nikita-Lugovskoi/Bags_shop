from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from bags.models import Order, OrderItem
from bags.utils import get_cart_statistics
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Очищает старые корзины (заказы со статусом "new") старше указанного количества дней'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Количество дней, после которых корзины считаются старыми (по умолчанию: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, что будет удалено, без фактического удаления'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно удалить все старые корзины без подтверждения'
        )
        parser.add_argument(
            '--notify',
            action='store_true',
            help='Отправить уведомление администратору после очистки'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        force = options['force']
        notify = options['notify']

        # Вычисляем дату отсечения
        cutoff_date = timezone.now() - timedelta(days=days)

        # Находим старые корзины
        old_carts = Order.objects.filter(
            status='new',
            created_at__lt=cutoff_date
        )

        old_carts_count = old_carts.count()

        if old_carts_count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'Старых корзин (старше {days} дней) не найдено.')
            )
            return

        # Подсчитываем количество элементов заказов
        total_items = OrderItem.objects.filter(
            order__in=old_carts
        ).count()

        self.stdout.write(
            f'Найдено {old_carts_count} старых корзин с {total_items} товарами '
            f'(старше {days} дней, созданы до {cutoff_date.strftime("%d.%m.%Y %H:%M")})'
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА: '
                    'Ничего не будет удалено. Используйте --force для удаления.'
                )
            )

            # Показываем детали старых корзин
            for cart in old_carts[:10]:  # Показываем первые 10
                self.stdout.write(
                    f'  - Корзина #{cart.id} пользователя {cart.user.email} '
                    f'(создана: {cart.created_at.strftime("%d.%m.%Y %H:%M")})'
                )

            if old_carts_count > 10:
                self.stdout.write(f'  ... и еще {old_carts_count - 10} корзин')

            return

        if not force:
            # Запрашиваем подтверждение
            confirm = input(
                f'\nВы уверены, что хотите удалить {old_carts_count} корзин '
                f'с {total_items} товарами? (yes/no): '
            )

            if confirm.lower() not in ['yes', 'y', 'да', 'д']:
                self.stdout.write(
                    self.style.WARNING('Операция отменена.')
                )
                return

        # Выполняем удаление
        try:
            with transaction.atomic():
                # Сначала удаляем элементы заказов
                deleted_items = OrderItem.objects.filter(
                    order__in=old_carts
                ).delete()

                # Затем удаляем сами заказы
                deleted_carts = old_carts.delete()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Успешно удалено:\n'
                        f'  - {deleted_carts[0]} корзин\n'
                        f'  - {deleted_items[0]} элементов заказов'
                    )
                )

                logger.info(
                    f'Очистка корзин: удалено {deleted_carts[0]} корзин '
                    f'с {deleted_items[0]} товарами (старше {days} дней)'
                )

                # Отправляем уведомление если запрошено
                if notify:
                    self.stdout.write('\n📧 Отправка уведомления о результатах очистки...')

                    # Получаем обновленную статистику
                    stats = get_cart_statistics()

                    # Создаем специальное уведомление о результатах очистки
                    subject = f"✅ Очистка корзин завершена - удалено {deleted_carts[0]} корзин"

                    message = f"""
ОЧИСТКА КОРЗИН ЗАВЕРШЕНА!

Результаты очистки:
- Удалено корзин: {deleted_carts[0]}
- Удалено товаров: {deleted_items[0]}
- Возраст корзин: старше {days} дней

Текущая статистика после очистки:
- Всего корзин: {stats['total_carts']}
- Товаров в корзинах: {stats['total_cart_items']}
- Старых корзин (>7 дней): {stats['old_carts_7_days']}
- Старых корзин (>30 дней): {stats['old_carts_30_days']}

Очистка выполнена: {timezone.now().strftime('%d.%m.%Y %H:%M')}
"""

                    html_message = f"""
<html>
  <body style='font-family:Arial,sans-serif;background:#f8f9fa;padding:0;margin:0;'>
    <div style='max-width:600px;margin:30px auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.07);overflow:hidden;'>
      <div style='background:linear-gradient(90deg,#4caf50,#66bb6a);color:#fff;padding:24px 32px 16px 32px;'>
        <h2 style='margin:0 0 8px 0;font-weight:700;'>✅ Очистка корзин завершена</h2>
        <div style='font-size:1.1rem;'>Удалено {deleted_carts[0]} корзин</div>
      </div>
      <div style='padding:24px 32px;'>
        <h3 style='margin-top:0;color:#4caf50;'>📊 Результаты очистки</h3>
        <div style='background:#f8f9fa;padding:16px;border-radius:8px;margin-bottom:16px;'>
          <p style='margin:0 0 8px 0;'><b>Удалено корзин:</b> {deleted_carts[0]}</p>
          <p style='margin:0 0 8px 0;'><b>Удалено товаров:</b> {deleted_items[0]}</p>
          <p style='margin:0;'><b>Возраст корзин:</b> старше {days} дней</p>
        </div>

        <h3 style='color:#4caf50;'>📈 Текущая статистика</h3>
        <div style='background:#e8f5e8;border:1px solid #c8e6c9;border-radius:8px;padding:16px;margin-bottom:16px;'>
          <p style='margin:0 0 8px 0;'><b>Всего корзин:</b> {stats['total_carts']}</p>
          <p style='margin:0 0 8px 0;'><b>Товаров в корзинах:</b> {stats['total_cart_items']}</p>
          <p style='margin:0 0 8px 0;'><b>Старых корзин (>7 дней):</b> {stats['old_carts_7_days']}</p>
          <p style='margin:0;'><b>Старых корзин (>30 дней):</b> {stats['old_carts_30_days']}</p>
        </div>

        <div style='background:#e3f2fd;border:1px solid #bbdefb;border-radius:8px;padding:16px;margin-top:16px;'>
          <p style='margin:0;color:#1976d2;font-size:0.9rem;'><i>💡 Очистка выполнена: {timezone.now().strftime('%d.%m.%Y %H:%M')}</i></p>
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
                        from django.core.mail import send_mail
                        from django.conf import settings

                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[settings.DEFAULT_FROM_EMAIL],
                            fail_silently=False,
                            html_message=html_message,
                        )

                        self.stdout.write(
                            self.style.SUCCESS(
                                '✅ Уведомление о результатах очистки отправлено'
                            )
                        )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'❌ Ошибка при отправке уведомления: {e}'
                            )
                        )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при удалении: {e}')
            )
            logger.error(f'Ошибка при очистке корзин: {e}')
            return

        # Показываем статистику после очистки
        remaining_carts = Order.objects.filter(status='new').count()
        remaining_items = OrderItem.objects.filter(
            order__status='new'
        ).count()

        self.stdout.write(
            '\nСтатистика после очистки:\n'
            f'  - Осталось корзин: {remaining_carts}\n'
            f'  - Осталось товаров в корзинах: {remaining_items}'
        )

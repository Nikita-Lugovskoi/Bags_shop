from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from bags.models import Order, OrderItem
from django.db.models import Count, Sum, Avg
from bags.utils import send_cleanup_notification, get_cart_statistics


class Command(BaseCommand):
    help = 'Показывает статистику корзин и заказов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Количество дней для анализа (по умолчанию: 30)'
        )
        parser.add_argument(
            '--notify',
            action='store_true',
            help='Отправить уведомление администратору если требуется очистка'
        )

    def handle(self, *args, **options):
        days = options['days']
        notify = options['notify']
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.SUCCESS(f'📊 СТАТИСТИКА КОРЗИН И ЗАКАЗОВ (за последние {days} дней)')
        )
        self.stdout.write('=' * 60)

        # Общая статистика
        total_orders = Order.objects.count()
        total_carts = Order.objects.filter(status='new').count()
        total_items = OrderItem.objects.count()
        total_cart_items = OrderItem.objects.filter(order__status='new').count()

        self.stdout.write('\n📈 ОБЩАЯ СТАТИСТИКА:')
        self.stdout.write(f'  Всего заказов: {total_orders}')
        self.stdout.write(f'  Активных корзин: {total_carts}')
        self.stdout.write(f'  Всего товаров в заказах: {total_items}')
        self.stdout.write(f'  Товаров в корзинах: {total_cart_items}')

        # Статистика по статусам
        self.stdout.write('\n🏷️ СТАТИСТИКА ПО СТАТУСАМ:')
        status_stats = Order.objects.values('status').annotate(
            count=Count('id'),
            total_price=Sum('total_price')
        ).order_by('status')

        for stat in status_stats:
            status_display = dict(Order.STATUS_CHOICES)[stat['status']]
            self.stdout.write(
                f'  {status_display}: {stat["count"]} заказов '
                f'(сумма: {stat["total_price"] or 0:.2f} ₽)'
            )

        # Старые корзины
        old_carts = Order.objects.filter(
            status='new',
            created_at__lt=cutoff_date
        )
        old_carts_count = old_carts.count()
        old_carts_items = OrderItem.objects.filter(order__in=old_carts).count()

        self.stdout.write(f'\n🗑️ СТАРЫЕ КОРЗИНЫ (старше {days} дней):')
        self.stdout.write(f'  Количество: {old_carts_count}')
        self.stdout.write(f'  Товаров в них: {old_carts_items}')

        if old_carts_count > 0:
            avg_age = old_carts.aggregate(
                avg_age=Avg(timezone.now() - timezone.F('created_at'))
            )['avg_age']
            avg_days = avg_age.days if avg_age else 0
            self.stdout.write(f'  Средний возраст: {avg_days} дней')

        # Статистика по пользователям
        self.stdout.write('\n👥 СТАТИСТИКА ПО ПОЛЬЗОВАТЕЛЯМ:')
        users_with_carts = Order.objects.filter(status='new').values('user').distinct().count()
        users_with_orders = Order.objects.exclude(status='new').values('user').distinct().count()

        self.stdout.write(f'  Пользователей с корзинами: {users_with_carts}')
        self.stdout.write(f'  Пользователей с заказами: {users_with_orders}')

        # Топ корзин по количеству товаров
        self.stdout.write('\n📦 ТОП-5 КОРЗИН ПО КОЛИЧЕСТВУ ТОВАРОВ:')
        top_carts = Order.objects.filter(status='new').annotate(
            items_count=Count('orderitem')
        ).order_by('-items_count')[:5]

        for i, cart in enumerate(top_carts, 1):
            self.stdout.write(
                f'  {i}. Корзина #{cart.id} ({cart.user.email}): '
                f'{cart.items_count} товаров, {cart.total_price} ₽'
            )

        # Рекомендации
        self.stdout.write('\n💡 РЕКОМЕНДАЦИИ:')

        if old_carts_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠️ Найдено {old_carts_count} старых корзин. '
                    f'Рекомендуется очистка: python manage.py cleanup_old_carts'
                )
            )

        if total_carts > 1000:
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠️ Много активных корзин ({total_carts}). '
                    f'Рассмотрите автоматическую очистку.'
                )
            )

        if total_cart_items > 5000:
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠️ Много товаров в корзинах ({total_cart_items}). '
                    f'Может влиять на производительность.'
                )
            )

        # Отправка уведомления если запрошено
        if notify:
            stats = get_cart_statistics()
            if send_cleanup_notification(stats):
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n📧 Уведомление отправлено администратору '
                        f'(старых корзин: {stats["old_carts_30_days"]})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✅ Уведомление не требуется (старых корзин нет)'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS('\n✅ Статистика успешно сгенерирована!')
        )

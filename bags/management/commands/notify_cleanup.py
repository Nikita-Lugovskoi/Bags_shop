from django.core.management.base import BaseCommand
from bags.utils import get_cart_statistics, send_cleanup_notification


class Command(BaseCommand):
    help = 'Отправляет уведомление администратору о необходимости очистки корзин'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно отправить уведомление даже если старых корзин нет'
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=30,
            help='Пороговое количество дней для уведомления (по умолчанию: 30)'
        )

    def handle(self, *args, **options):
        force = options['force']
        threshold = options['threshold']

        self.stdout.write(
            self.style.SUCCESS('🔍 Проверка необходимости очистки корзин...')
        )

        # Получаем статистику корзин
        stats = get_cart_statistics()

        self.stdout.write('\n📊 СТАТИСТИКА КОРЗИН:')
        self.stdout.write(f'  Всего корзин: {stats["total_carts"]}')
        self.stdout.write(f'  Товаров в корзинах: {stats["total_cart_items"]}')
        self.stdout.write(f'  Старых корзин (>7 дней): {stats["old_carts_7_days"]}')
        self.stdout.write(f'  Старых корзин (>30 дней): {stats["old_carts_30_days"]}')

        # Проверяем, нужно ли отправлять уведомление
        if stats['old_carts_30_days'] == 0 and not force:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n✅ Уведомление не требуется - старых корзин не найдено'
                )
            )
            return

        if force and stats['old_carts_30_days'] == 0:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️ Принудительная отправка уведомления (старых корзин нет)'
                )
            )

        # Отправляем уведомление
        self.stdout.write('\n📧 Отправка уведомления администратору...')

        # Для принудительной отправки создаем тестовую статистику
        if force and stats['old_carts_30_days'] == 0:
            test_stats = stats.copy()
            test_stats['old_carts_30_days'] = 5  # Тестовое значение
            notification_sent = send_cleanup_notification(test_stats, threshold)
        else:
            notification_sent = send_cleanup_notification(stats, threshold)

        if notification_sent:
            self.stdout.write(
                self.style.SUCCESS(
                    '✅ Уведомление успешно отправлено!'
                )
            )

            # Показываем детали уведомления
            if force and stats['old_carts_30_days'] == 0:
                level = "ТЕСТОВЫЙ"
            elif stats['old_carts_30_days'] > 100:
                level = "КРИТИЧЕСКИЙ"
            elif stats['old_carts_30_days'] > 50:
                level = "ВЫСОКИЙ"
            else:
                level = "СРЕДНИЙ"

            self.stdout.write(f'  Уровень критичности: {level}')
            if force and stats['old_carts_30_days'] == 0:
                self.stdout.write('  Тестовых корзин: 5')
            else:
                self.stdout.write(f'  Старых корзин: {stats["old_carts_30_days"]}')

        else:
            self.stdout.write(
                self.style.ERROR(
                    '❌ Ошибка при отправке уведомления'
                )
            )

from django.core.management import BaseCommand

from users.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        admin_user = User.objects.create(
            email='admin@bags.ru',
            first_name='Admin',
            last_name='Adminov',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            is_active=True,

        )
        admin_user.set_password('qwerty')
        admin_user.save()
        print('Admin Created')

        moderator = User.objects.create(
            email='moderator@bags.ru',
            first_name='Moderator',
            last_name='Moderatorov',
            role=User.Role.MANAGER,
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        moderator.set_password('qwerty')
        moderator.save()
        print('Moderator Created')

        user = User.objects.create(
            email='user@bags.ru',
            first_name='User',
            last_name='Userov',
            role=User.Role.USER,
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        user.set_password('qwerty')
        user.save()
        print('User Created')

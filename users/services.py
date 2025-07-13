import random
import string
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse


def send_register_email(email):
    """
    Отправка приветственного письма после регистрации
    """
    subject = 'Добро пожаловать в магазин сумочек из бусин!'
    message = '''
    Здравствуйте!

    Спасибо за регистрацию в нашем магазине сумочек из бусин!

    Теперь вы можете:
    - Просматривать каталог товаров
    - Добавлять товары в корзину
    - Оформлять заказы
    - Отслеживать статус заказов
    - Получать уведомления о новых поступлениях

    Если у вас возникнут вопросы, мы всегда готовы помочь!

    С уважением,
    Команда магазина сумочек из бусин
    '''
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )


def generate_verification_code():
    """
    Генерация кода подтверждения
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def send_verification_code(email, code):
    """
    Отправка письма с ссылкой для подтверждения email
    """
    from django.conf import settings
    
    # Проверяем, настроен ли email
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise Exception("Email настройки не найдены. Установите EMAIL_HOST_USER и EMAIL_HOST_PASSWORD в переменных окружения.")
    
    verification_url = f"{settings.SITE_URL}{reverse('users:verify_email', args=[code])}"
    subject = 'Подтверждение регистрации'
    message = f'''
    Здравствуйте!

    Спасибо за регистрацию в нашем магазине сумочек из бусин!

    Для подтверждения вашего email, пожалуйста, перейдите по следующей ссылке:

    <a href="{verification_url}">{verification_url}</a>

    Ссылка действительна в течение 24 часов.

    Если вы не регистрировались в нашем магазине, просто проигнорируйте это письмо.

    С уважением,
    Команда магазина сумочек из бусин
    '''
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
            html_message=message,
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка отправки verification email: {e}')
        raise Exception(f"Не удалось отправить письмо подтверждения: {str(e)}")


def send_email_verification(user, new_email):
    """Отправка письма для подтверждения нового email"""
    verification_url = f"{settings.SITE_URL}{reverse('users:verify_email_token', args=[user.email_verification_token])}"

    print(f"DEBUG: Генерируем ссылку: {verification_url}")  # Отладочная информация
    print(f"DEBUG: Токен пользователя: {user.email_verification_token}")  # Отладочная информация

    subject = 'Подтверждение нового email'
    message = f'''
    Здравствуйте!

    Вы запросили смену email в нашем магазине сумочек из бусин.

    Для подтверждения нового email, пожалуйста, перейдите по следующей ссылке:

    <a href="{verification_url}">{verification_url}</a>

    Если вы не запрашивали смену email, просто проигнорируйте это письмо.

    С уважением,
    Команда магазина сумочек из бусин
    '''

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[new_email],
        fail_silently=False,
        html_message=message,
    )


def send_password_verification(user):
    """Отправка письма для подтверждения смены пароля"""
    verification_url = f"{settings.SITE_URL}{reverse('users:verify_password_token', args=[user.password_verification_token])}"

    print(f"DEBUG: Генерируем ссылку для пароля: {verification_url}")  # Отладочная информация
    print(f"DEBUG: Токен пароля пользователя: {user.password_verification_token}")  # Отладочная информация

    subject = 'Подтверждение смены пароля'
    message = f'''
    Здравствуйте!

    Вы запросили смену пароля в нашем магазине сумочек из бусин.

    Для подтверждения смены пароля, пожалуйста, перейдите по следующей ссылке:

    <a href="{verification_url}">{verification_url}</a>

    Если вы не запрашивали смену пароля, просто проигнорируйте это письмо.

    С уважением,
    Команда магазина сумочек из бусин
    '''

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False,
        html_message=message,
    )

import re
import hashlib
import secrets
from django.core.cache import cache


def sanitize_filename(filename):
    """
    Очищает имя файла от потенциально опасных символов
    """
    # Удаляем опасные символы
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Ограничиваем длину
    if len(filename) > 255:
        filename = filename[:255]
    return filename


def generate_secure_token(length=50):
    """
    Генерирует криптографически безопасный токен
    """
    return secrets.token_urlsafe(length)


def hash_sensitive_data(data):
    """
    Хеширует чувствительные данные для логирования
    """
    if isinstance(data, str):
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    return str(data)[:8] + '***'


def is_suspicious_ip(ip):
    """
    Проверяет IP на подозрительную активность
    """
    cache_key = f'suspicious_ip_{ip}'
    attempts = cache.get(cache_key, 0)
    return attempts > 10


def log_security_event(event_type, user_id=None, ip=None, details=None):
    """
    Логирует события безопасности
    """
    import logging
    logger = logging.getLogger('django.security')

    log_data = {
        'event_type': event_type,
        'user_id': user_id,
        'ip': hash_sensitive_data(ip) if ip else None,
        'details': details
    }

    logger.warning(f'Security event: {log_data}')


def validate_password_strength(password):
    """
    Проверяет сложность пароля
    """
    errors = []

    if len(password) < 8:
        errors.append('Пароль должен содержать минимум 8 символов')

    if not re.search(r'[A-Z]', password):
        errors.append('Пароль должен содержать хотя бы одну заглавную букву')

    if not re.search(r'[a-z]', password):
        errors.append('Пароль должен содержать хотя бы одну строчную букву')

    if not re.search(r'\d', password):
        errors.append('Пароль должен содержать хотя бы одну цифру')

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Пароль должен содержать хотя бы один специальный символ')

    return errors


def rate_limit_request(request, key_prefix, limit=100, window=3600):
    """
    Ограничивает количество запросов с одного IP
    """
    ip = get_client_ip(request)
    cache_key = f'{key_prefix}_{ip}'

    requests = cache.get(cache_key, 0)
    if requests >= limit:
        return False

    cache.set(cache_key, requests + 1, window)
    return True


def get_client_ip(request):
    """
    Получает реальный IP адрес клиента
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_file_safety(file):
    """
    Проверяет файл на безопасность
    """
    # Проверяем MIME тип
    allowed_mimes = ['image/jpeg', 'image/jpg', 'image/png']
    if hasattr(file, 'content_type') and file.content_type not in allowed_mimes:
        return False, 'Недопустимый тип файла'

    # Проверяем размер
    if file.size > 5 * 1024 * 1024:  # 5MB
        return False, 'Файл слишком большой'

    # Проверяем имя файла
    if re.search(r'[<>:"/\\|?*]', file.name):
        return False, 'Недопустимые символы в имени файла'

    return True, 'OK'

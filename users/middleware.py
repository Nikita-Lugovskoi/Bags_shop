from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.conf import settings


class BruteForceProtectionMiddleware:
    """
    Middleware для защиты от brute force атак
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем только POST запросы на страницы входа
        if request.method == 'POST' and request.path.endswith('/login/'):
            ip = self.get_client_ip(request)
            cache_key = f'login_attempts_{ip}'

            # Получаем количество попыток входа
            attempts = cache.get(cache_key, 0)

            if attempts >= getattr(settings, 'LOGIN_ATTEMPT_LIMIT', 5):
                return HttpResponseForbidden(
                    'Слишком много попыток входа. Попробуйте позже.'
                )

            # Увеличиваем счетчик попыток
            cache.set(cache_key, attempts + 1, getattr(settings, 'LOGIN_ATTEMPT_TIMEOUT', 300))

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware для добавления заголовков безопасности
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Добавляем заголовки безопасности
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Добавляем заголовки для HTTPS (раскомментировать для продакшена)
        # response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


class RequestLoggingMiddleware:
    """
    Middleware для логирования подозрительных запросов
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Логируем подозрительные запросы
        if self.is_suspicious_request(request):
            import logging
            logger = logging.getLogger('django.security')
            logger.warning(
                f'Suspicious request from {self.get_client_ip(request)}: '
                f'{request.method} {request.path}'
            )

        response = self.get_response(request)
        return response

    def is_suspicious_request(self, request):
        """Определяет подозрительные запросы"""
        suspicious_patterns = [
            '/admin/',  # Попытки доступа к админке
            'script',   # Попытки XSS
            'union',    # SQL injection
            'select',   # SQL injection
            'drop',     # SQL injection
        ]

        path = request.path.lower()
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

        # Проверяем паттерны в пути
        for pattern in suspicious_patterns:
            if pattern in path:
                return True

        # Проверяем подозрительные User-Agent
        suspicious_agents = ['sqlmap', 'nikto', 'nmap', 'scanner']
        for agent in suspicious_agents:
            if agent in user_agent:
                return True

        return False

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# Реализация куки на сайте магазина сумок

## 📋 Обзор

Данный документ описывает полную реализацию системы куки на сайте магазина сумок из бусин. Система включает в себя функциональные, аналитические и сессионные куки с соблюдением требований российского законодательства.

## 🍪 Типы используемых куки

### 1. Сессионные куки (Session Cookies)
- **Назначение**: Хранение данных сессии пользователя
- **Время жизни**: До закрытия браузера или 30 дней
- **Примеры**: 
  - `sessionid` - идентификатор сессии Django
  - `csrftoken` - токен CSRF для безопасности
  - `cart` - данные корзины

### 2. Функциональные куки (Functional Cookies)
- **Назначение**: Сохранение пользовательских предпочтений
- **Время жизни**: 1 год
- **Примеры**:
  - `user_pref_theme` - тема оформления
  - `user_pref_font_size` - размер шрифта
  - `remember_me` - "Запомнить меня"

### 3. Аналитические куки (Analytics Cookies)
- **Назначение**: Сбор статистики посещений
- **Время жизни**: 30 дней - 1 год
- **Примеры**:
  - `analytics_first_visit` - первый визит
  - `analytics_last_visit` - последний визит
  - `analytics_visit_count` - количество визитов

## 🔧 Техническая реализация

### Настройки в settings.py

```python
# Настройки корзины
CART_SESSION_ID = 'cart'

# Настройки сессий
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 дней
SESSION_COOKIE_SECURE = False  # True для HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Настройки CSRF
CSRF_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 дней
CSRF_COOKIE_SECURE = False  # True для HTTPS
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

### Middleware для аналитики

```python
class AnalyticsMiddleware:
    """
    Middleware для сбора аналитических данных через куки
    """
    
    def set_analytics_cookies(self, request, response):
        # Куки для отслеживания первого посещения
        if 'first_visit' not in request.COOKIES:
            response.set_cookie(
                'first_visit',
                timezone.now().isoformat(),
                max_age=60*60*24*365,  # 1 год
                httponly=False,
                samesite='Lax'
            )
        
        # Куки для отслеживания последнего посещения
        response.set_cookie(
            'last_visit',
            timezone.now().isoformat(),
            max_age=60*60*24*30,  # 30 дней
            httponly=False,
            samesite='Lax'
        )
        
        # Куки для подсчета посещений
        visit_count = int(request.COOKIES.get('visit_count', 0)) + 1
        response.set_cookie(
            'visit_count',
            visit_count,
            max_age=60*60*24*365,  # 1 год
            httponly=False,
            samesite='Lax'
        )
```

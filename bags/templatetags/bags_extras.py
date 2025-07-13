from django import template
# from decimal import Decimal

register = template.Library()


@register.filter
def multiply(value, arg):
    """
    Умножает значение на аргумент

    Args:
        value: Первый множитель
        arg: Второй множитель

    Returns:
        float: Результат умножения
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def get_item(dictionary, key):
    """
    Получение значения из словаря по ключу
    Args:
        dictionary: Словарь
        key: Ключ
    Returns:
        Значение из словаря по ключу или None, если ключ не найден
    """
    try:
        return dictionary.get(int(key))
    except (ValueError, TypeError):
        return dictionary.get(key)

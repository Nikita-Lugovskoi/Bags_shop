#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bags.models import Product
import secrets

def fill_slugs():
    products = Product.objects.all()
    for product in products:
        if not product.slug:
            # Генерируем уникальный слаг
            new_slug = secrets.token_urlsafe(8).replace('-', '').replace('_', '')[:12]
            # Проверяем уникальность
            while Product.objects.filter(slug=new_slug).exists():
                new_slug = secrets.token_urlsafe(8).replace('-', '').replace('_', '')[:12]
            product.slug = new_slug
            product.save(update_fields=['slug'])
            print(f"Слаг для товара '{product.name}': {product.slug}")
    
    print(f"Заполнено слагов: {products.count()}")

if __name__ == '__main__':
    fill_slugs() 
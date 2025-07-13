from django import forms
from .models import Order, Review
import re


class OrderForm(forms.ModelForm):
    """
    Форма для оформления заказа
    """
    privacy_agreement = forms.BooleanField(
        required=True,
        label='Я согласен на обработку персональных данных',
        help_text='Нажимая кнопку "Оформить заказ", вы даете согласие на обработку персональных данных в соответствии с <a href="/privacy-policy/" target="_blank">Политикой конфиденциальности</a>.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'postal_code', 'comment'
        ]
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем классы Bootstrap для всех полей
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'

        # Специальные настройки для поля телефона
        self.fields['phone'].widget.attrs.update({
            'placeholder': '+7 (___) ___-__-__',
            'data-mask': 'phone',
            'autocomplete': 'tel'
        })

        # Настройки для поля согласия
        self.fields['privacy_agreement'].widget.attrs.update({
            'class': 'form-check-input',
            'id': 'privacy_agreement'
        })

    def clean_phone(self):
        """
        Валидация номера телефона
        """
        phone = self.cleaned_data.get('phone')
        if phone:
            # Убираем все нецифровые символы
            digits_only = re.sub(r'\D', '', phone)

            # Проверяем, что номер содержит 11 цифр и начинается с 7
            if len(digits_only) != 11 or not digits_only.startswith('7'):
                raise forms.ValidationError(
                    'Введите корректный номер телефона в формате +7 (XXX) XXX-XX-XX'
                )

            # Форматируем номер для сохранения
            formatted_phone = f"+7 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:9]}-{digits_only[9:11]}"
            return formatted_phone

        return phone


class EditOrderForm(forms.ModelForm):
    """
    Форма для редактирования заказа (без поля согласия)
    """
    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'postal_code', 'comment'
        ]
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем классы Bootstrap для всех полей
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # Специальные настройки для поля телефона
        self.fields['phone'].widget.attrs.update({
            'placeholder': '+7 (___) ___-__-__',
            'data-mask': 'phone',
            'autocomplete': 'tel'
        })

    def clean_phone(self):
        """
        Валидация номера телефона
        """
        phone = self.cleaned_data.get('phone')
        if phone:
            # Убираем все нецифровые символы
            digits_only = re.sub(r'\D', '', phone)

            # Проверяем, что номер содержит 11 цифр и начинается с 7
            if len(digits_only) != 11 or not digits_only.startswith('7'):
                raise forms.ValidationError(
                    'Введите корректный номер телефона в формате +7 (XXX) XXX-XX-XX'
                )

            # Форматируем номер для сохранения
            formatted_phone = f"+7 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:9]}-{digits_only[9:11]}"
            return formatted_phone

        return phone


class ReviewForm(forms.ModelForm):
    """
    Форма для добавления отзыва
    """
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, f"{i} {'★' * i}") for i in range(1, 6)],
                attrs={'class': 'rating-radio'}
            ),
            'text': forms.Textarea(
                attrs={
                    'rows': 4,
                    'class': 'form-control',
                    'placeholder': 'Напишите ваш отзыв о товаре...'
                }
            ),
        }
        labels = {
            'rating': 'Оценка',
            'text': 'Ваш отзыв'
        }

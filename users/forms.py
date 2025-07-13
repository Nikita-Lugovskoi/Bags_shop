from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password

from users.models import User
from django.contrib.auth.forms import AuthenticationForm


class StyleFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'


class UserForm(StyleFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role')


class UserRegisterForm(StyleFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=250, required=True, label='Имя')
    last_name = forms.CharField(max_length=250, required=True, label='Фамилия')
    privacy_agreement = forms.BooleanField(
        required=True,
        label='Я согласен на обработку персональных данных',
        help_text='Нажимая кнопку "Зарегистрироваться", вы даете согласие на обработку персональных данных в соответствии с <a href="/privacy-policy/" target="_blank">Политикой конфиденциальности</a>.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def clean_password2(self):
        cleaned_data = self.cleaned_data
        validate_password(cleaned_data['password1'])
        if cleaned_data['password1'] != cleaned_data['password2']:
            raise forms.ValidationError('Пароли не совпадают')
        return cleaned_data['password2']


class UserLoginForm(StyleFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'Введите ваш email'})
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        label='Запомнить меня',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class UserUpdateForm(StyleFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'avatar')
        widgets = {
            'avatar': forms.FileInput(attrs={'accept': 'image/*'}),
            'email': forms.EmailInput(attrs={'readonly': 'readonly', 'style': 'background-color: #f8f9fa;'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Если есть ожидающий подтверждения email, показываем его в подсказке
        if self.instance and self.instance.new_email:
            self.fields['email'].help_text = f'Ожидает подтверждения: {self.instance.new_email}'
            self.fields['email'].widget.attrs['placeholder'] = f'Текущий: {self.instance.email}'
        else:
            # Если нет ожидающего, показываем сообщение о том, что email нельзя изменить
            self.fields['email'].help_text = 'Email нельзя изменить через эту форму. Обратитесь к администратору.'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Всегда возвращаем текущий email пользователя, игнорируя любые изменения
        return self.instance.email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise forms.ValidationError('Имя не может быть пустым')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise forms.ValidationError('Фамилия не может быть пустой')
        return last_name

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Проверяем размер файла (5MB)
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Размер файла не должен превышать 5MB')

            # Проверяем тип файла
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            if avatar.content_type not in allowed_types:
                raise forms.ValidationError('Разрешены только файлы JPEG и PNG')

            # Проверяем расширение файла
            import os
            ext = os.path.splitext(avatar.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                raise forms.ValidationError('Разрешены только файлы с расширениями .jpg, .jpeg, .png')

            # Проверяем на вредоносный контент (базовая проверка)
            if avatar.name.lower().find('script') != -1:
                raise forms.ValidationError('Недопустимое имя файла')

        return avatar


class ChangeEmailForm(StyleFormMixin, forms.Form):
    new_email = forms.EmailField(
        label='Новый email',
        help_text='Введите новый email адрес'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Текущий пароль',
        help_text='Введите ваш текущий пароль для подтверждения'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email')

        # Проверяем, не занят ли email другим пользователем
        if User.objects.filter(email=new_email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Этот email уже используется')

        # Проверяем, не пытается ли пользователь установить тот же email
        if new_email == self.user.email:
            raise forms.ValidationError('Этот email уже используется в вашем аккаунте')

        return new_email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.user.check_password(password):
            raise forms.ValidationError('Неверный пароль')
        return password


class ChangePasswordForm(StyleFormMixin, forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Текущий пароль',
        help_text='Введите ваш текущий пароль для подтверждения'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(),
        label='Новый пароль',
        help_text='Введите новый пароль'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(),
        label='Подтверждение нового пароля',
        help_text='Повторите новый пароль'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError('Неверный текущий пароль')
        return current_password

    def clean_new_password2(self):
        new_password1 = self.cleaned_data.get('new_password1')
        new_password2 = self.cleaned_data.get('new_password2')
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError('Пароли не совпадают')
        validate_password(new_password2, self.user)
        return new_password2

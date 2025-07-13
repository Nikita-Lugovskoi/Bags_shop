import random
import string
from datetime import timedelta
from django.utils import timezone

from django.shortcuts import reverse, redirect
from django.http import HttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import (
    LoginView, PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.views.generic import CreateView, UpdateView, FormView, View, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin

from users.models import User
from users.forms import UserRegisterForm, UserLoginForm, UserUpdateForm, ChangeEmailForm, ChangePasswordForm
from users.services import send_register_email, send_verification_code, generate_verification_code

User = get_user_model()


class UserRegisterView(CreateView):
    """
    Представление для регистрации пользователя
    """
    model = User
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:email_verification_status')

    def form_valid(self, form):
        response = super().form_valid(form)
        email = form.cleaned_data.get('email')
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')

        # Устанавливаем роль USER для всех новых пользователей
        user = form.instance
        user.is_verified = False  # Требуем подтверждения email
        user.role = User.Role.USER  # Устанавливаем роль USER
        user.first_name = first_name
        user.last_name = last_name

        # Генерируем код подтверждения
        verification_code = generate_verification_code()
        user.verification_code = verification_code
        user.verification_code_created_at = timezone.now()
        user.save()

        # Отправляем письмо с кодом подтверждения
        try:
            send_verification_code(email, verification_code)
            messages.info(self.request, 'Регистрация успешна! Проверьте вашу почту для подтверждения email.')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка отправки email при регистрации: {e}')
            
            # Проверяем, настроен ли email
            from django.conf import settings
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                messages.warning(self.request, 
                    'Регистрация успешна! Email не настроен на сервере. '
                    'Обратитесь к администратору для подтверждения аккаунта.')
            else:
                messages.error(self.request, 
                    'Регистрация успешна! Ошибка отправки письма подтверждения. '
                    'Обратитесь к администратору.')
            
            # В случае ошибки отправки, все равно создаем пользователя, но он не подтвержден

        return response


class UserLoginView(LoginView):
    """
    Представление для входа пользователя
    """
    form_class = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('bags:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(f"DEBUG: Форма в контексте: {context.get('form')}")
        if context.get('form'):
            print(f"DEBUG: Поля формы: {list(context['form'].fields.keys())}")
        return context

    def form_valid(self, form):
        user = form.get_user()
        # Пропускаем проверку для администраторов
        if not user.is_verified and not (user.is_staff or user.is_superuser):
            messages.error(self.request, 'Пожалуйста, подтвердите ваш email перед входом в систему.')
            return self.form_invalid(form)

        # Обрабатываем "Запомнить меня"
        remember_me = form.cleaned_data.get('remember_me', False)
        if not remember_me:
            # Если не выбрано "Запомнить меня", сессия истечет при закрытии браузера
            self.request.session.set_expiry(0)

        return super().form_valid(form)


class UserProfileView(LoginRequiredMixin, TemplateView):
    """
    Представление для отображения профиля пользователя
    """
    template_name = 'users/user_profile_read_only.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        # Фильтруем заказы, исключая корзину и отмененные
        context['orders'] = self.request.user.order_set.exclude(status__in=['new', 'cancelled'])
        return context


class UserUpdateView(UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'users/user_update.html'
    success_url = reverse_lazy('users:user_profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        # Сохраняем только имя, фамилию и аватар
        # Email не может быть изменен через эту форму
        form.save()
        messages.success(self.request, 'Профиль успешно обновлен')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data()
        context_data['title'] = f'Обновить профиль {self.get_object()}'
        # Добавляем информацию о статусе подтверждения email
        user = self.get_object()
        if user.new_email:
            context_data['email_pending'] = True
            context_data['pending_email'] = user.new_email
        return context_data


@login_required
def user_logout(request):
    """
    Представление для выхода пользователя
    """
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('bags:home')


def verify_email(request, code):
    """
    Представление для подтверждения email по ссылке
    """
    try:
        user = User.objects.get(verification_code=code)
        if user.verification_code_created_at and timezone.now() - user.verification_code_created_at < timedelta(hours=24):
            user.is_verified = True
            user.verification_code = None
            user.verification_code_created_at = None
            user.save()

            # Отправляем приветственное письмо
            try:
                send_register_email(user.email)
            except Exception:
                pass  # Игнорируем ошибки отправки приветственного письма

            messages.success(request, 'Email успешно подтвержден! Теперь вы можете войти в систему.')
        else:
            messages.error(request, 'Срок действия ссылки истек. Пожалуйста, зарегистрируйтесь снова.')
    except User.DoesNotExist:
        messages.error(request, 'Неверная ссылка подтверждения.')

    return redirect('users:email_verification_status')


class UserPasswordResetView(PasswordResetView):
    """
    Представление для сброса пароля
    """
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')
    extra_context = {
        'title': 'Сброс пароля'
    }

    def get_success_url(self):
        return reverse_lazy('users:password_reset_done')


class UserPasswordResetDoneView(PasswordResetDoneView):
    """
    Представление для подтверждения отправки письма
    """
    template_name = 'users/password_reset_done.html'
    extra_context = {
        'title': 'Письмо отправлено'
    }


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Представление для установки нового пароля
    """
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')
    extra_context = {
        'title': 'Установка нового пароля'
    }


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    """
    Представление для подтверждения успешной смены пароля
    """
    template_name = 'users/password_reset_complete.html'
    extra_context = {
        'title': 'Пароль изменен'
    }


class EmailVerificationStatusView(TemplateView):
    """
    Представление для отображения статуса подтверждения email
    """
    template_name = 'users/email_verification_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Подтверждение Email'

        # Проверяем, есть ли у пользователя ожидающий подтверждения email
        if self.request.user.is_authenticated and self.request.user.new_email:
            context['email_change_pending'] = True
            context['pending_email'] = self.request.user.new_email
            context['current_email'] = self.request.user.email

        return context


class EmailVerificationView(View):
    def get(self, request, token):
        print(f"DEBUG: Получен токен: {token}")  # Отладочная информация
        try:
            user = User.objects.get(email_verification_token=token)
            print(f"DEBUG: Найден пользователь: {user.email}")  # Отладочная информация
            if user.new_email:
                print(f"DEBUG: Новый email: {user.new_email}")  # Отладочная информация
                # Сохраняем старый email для логирования
                old_email = user.email
                # Обновляем email
                user.email = user.new_email
                user.email_verification_token = None
                user.new_email = None
                user.save()

                # Автоматически авторизуем пользователя после подтверждения
                login(request, user)

                messages.success(request, f'Email успешно обновлен с {old_email} на {user.email}!')
                print("DEBUG: Email обновлен и пользователь авторизован")  # Отладочная информация
            else:
                print("DEBUG: Нет нового email")  # Отладочная информация
                messages.error(request, 'Неверный токен подтверждения')
        except User.DoesNotExist:
            print(f"DEBUG: Пользователь с токеном {token} не найден")  # Отладочная информация
            messages.error(request, 'Неверный токен подтверждения')

        # Перенаправляем на главную страницу или профиль
        return redirect('bags:home')


class ChangeEmailView(LoginRequiredMixin, FormView):
    """
    Представление для смены email с подтверждением
    """
    form_class = ChangeEmailForm
    template_name = 'users/change_email.html'
    success_url = reverse_lazy('users:email_verification_status')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        new_email = form.cleaned_data.get('new_email')

        # Сохраняем новый email во временное поле
        user.new_email = new_email
        # Генерируем токен для подтверждения
        user.email_verification_token = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
        user.save()

        print(f"DEBUG: Сохранен токен: {user.email_verification_token}")  # Отладочная информация
        print(f"DEBUG: Сохранен новый email: {user.new_email}")  # Отладочная информация

        # Отправляем письмо с подтверждением
        try:
            from users.services import send_email_verification
            send_email_verification(user, new_email)
            messages.info(self.request, f'На новый email {new_email} отправлено письмо для подтверждения. Email будет изменён после подтверждения по ссылке.')
        except Exception as e:
            print(f"DEBUG: Ошибка отправки email: {e}")  # Отладочная информация
            messages.error(self.request, 'Ошибка отправки письма подтверждения. Email не изменен.')
            # Откатываем изменения
            user.new_email = None
            user.email_verification_token = None
            user.save()
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Смена email'
        return context


@login_required
def cancel_email_change(request):
    """
    Представление для отмены смены email
    """
    user = request.user
    if user.new_email:
        old_email = user.new_email
        user.new_email = None
        user.email_verification_token = None
        user.save()
        messages.success(request, f'Смена email на {old_email} отменена.')
    else:
        messages.info(request, 'Нет ожидающих подтверждения изменений email.')

    return redirect('users:user_profile')


class TestEmailVerificationView(View):
    """
    Тестовое представление для проверки ссылок подтверждения
    """
    def get(self, request):
        # Создаем тестовый токен
        test_token = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
        test_url = f"{settings.SITE_URL}{reverse('users:verify_email_token', args=[test_token])}"

        return HttpResponse(f"""
        <h1>Тест ссылки подтверждения email</h1>
        <p>Тестовый токен: {test_token}</p>
        <p>Тестовая ссылка: <a href="{test_url}">{test_url}</a></p>
        <p>SITE_URL: {settings.SITE_URL}</p>
        """)


class ChangePasswordView(LoginRequiredMixin, FormView):
    """
    Представление для смены пароля с подтверждением
    """
    form_class = ChangePasswordForm
    template_name = 'users/change_password.html'
    success_url = reverse_lazy('users:password_verification_status')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        new_password = form.cleaned_data.get('new_password1')

        # Сохраняем новый пароль во временное поле (зашифрованный)
        from django.contrib.auth.hashers import make_password
        user.new_password = make_password(new_password)
        # Генерируем токен для подтверждения
        user.password_verification_token = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
        user.save()

        print(f"DEBUG: Сохранен токен пароля: {user.password_verification_token}")  # Отладочная информация

        # Отправляем письмо с подтверждением
        try:
            from users.services import send_password_verification
            send_password_verification(user)
            messages.info(self.request, f'На ваш email {user.email} отправлено письмо для подтверждения смены пароля. Пароль будет изменён после подтверждения по ссылке.')
        except Exception as e:
            print(f"DEBUG: Ошибка отправки email для пароля: {e}")  # Отладочная информация
            messages.error(self.request, 'Ошибка отправки письма подтверждения. Пароль не изменен.')
            # Откатываем изменения
            user.new_password = None
            user.password_verification_token = None
            user.save()
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Смена пароля'
        return context


class PasswordVerificationView(View):
    def get(self, request, token):
        print(f"DEBUG: Получен токен пароля: {token}")  # Отладочная информация
        try:
            user = User.objects.get(password_verification_token=token)
            print(f"DEBUG: Найден пользователь для пароля: {user.email}")  # Отладочная информация
            if user.new_password:
                print("DEBUG: Новый пароль найден")  # Отладочная информация
                # Обновляем пароль
                user.password = user.new_password
                user.password_verification_token = None
                user.new_password = None
                user.save()

                # Автоматически авторизуем пользователя после подтверждения
                login(request, user)

                messages.success(request, 'Пароль успешно изменен!')
                print("DEBUG: Пароль обновлен и пользователь авторизован")  # Отладочная информация
            else:
                print("DEBUG: Нет нового пароля")  # Отладочная информация
                messages.error(request, 'Неверный токен подтверждения')
        except User.DoesNotExist:
            print(f"DEBUG: Пользователь с токеном пароля {token} не найден")  # Отладочная информация
            messages.error(request, 'Неверный токен подтверждения')

        # Перенаправляем на главную страницу
        return redirect('bags:home')


class PasswordVerificationStatusView(TemplateView):
    """
    Представление для отображения статуса подтверждения пароля
    """
    template_name = 'users/password_verification_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Подтверждение смены пароля'

        # Проверяем, есть ли у пользователя ожидающий подтверждения пароль
        if self.request.user.is_authenticated and self.request.user.new_password:
            context['password_change_pending'] = True
            context['current_email'] = self.request.user.email

        return context


@login_required
def cancel_password_change(request):
    """
    Представление для отмены смены пароля
    """
    user = request.user
    if user.new_password:
        user.new_password = None
        user.password_verification_token = None
        user.save()
        messages.success(request, 'Смена пароля отменена.')
    else:
        messages.info(request, 'Нет ожидающих подтверждения изменений пароля.')

    return redirect('users:user_profile')

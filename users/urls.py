from django.urls import path

from users.apps import UsersConfig
from users.views import (
    UserRegisterView, UserLoginView, UserProfileView,
    UserUpdateView, EmailVerificationView,
    UserPasswordResetView, UserPasswordResetDoneView, UserPasswordResetConfirmView,
    UserPasswordResetCompleteView, user_logout, verify_email, EmailVerificationStatusView,
    ChangeEmailView, TestEmailVerificationView, cancel_email_change, ChangePasswordView,
    PasswordVerificationView, PasswordVerificationStatusView, cancel_password_change
)

app_name = UsersConfig.name

urlpatterns = [
    path('', UserLoginView.as_view(), name='user_login'),
    path('logout/', user_logout, name='user_logout'),
    path('register/', UserRegisterView.as_view(), name='user_register'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('update/', UserUpdateView.as_view(), name='user_update'),
    path('change_email/', ChangeEmailView.as_view(), name='change_email'),
    path('cancel_email_change/', cancel_email_change, name='cancel_email_change'),
    path('change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('cancel_password_change/', cancel_password_change, name='cancel_password_change'),
    path('verify-email/<str:code>/', verify_email, name='verify_email'),
    path('verify-email-token/<str:token>/', EmailVerificationView.as_view(), name='verify_email_token'),
    path('verify-password-token/<str:token>/', PasswordVerificationView.as_view(), name='verify_password_token'),
    path('email-verification-status/', EmailVerificationStatusView.as_view(), name='email_verification_status'),
    path('password-verification-status/', PasswordVerificationStatusView.as_view(), name='password_verification_status'),
    path('test-email-verification/', TestEmailVerificationView.as_view(), name='test_email_verification'),
    path('password-reset/', UserPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', UserPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', UserPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

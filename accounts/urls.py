from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenVerifyView
from accounts.views import (
    RegisterView, LoginView, TokenRefreshView, VerifyEmailView,
    PasswordResetRequestView, PasswordResetConfirmView, ChangePasswordView,
    ProfileView, UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/verify-email/<uidb64>/<token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
]

urlpatterns += router.urls

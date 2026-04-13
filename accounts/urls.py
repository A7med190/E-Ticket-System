from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenVerifyView
from accounts.views import (
    RegisterView, LoginView, TokenRefreshView, VerifyEmailView,
    PasswordResetRequestView, PasswordResetConfirmView, ChangePasswordView,
    ProfileView, UserViewSet,
)

router = SimpleRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = router.urls + [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-email/<str:uidb64>/<str:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
from rest_framework import generics, viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from common.permissions import IsAdmin
from common.throttling import LoginThrottle
from accounts.serializers import (
    UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    ChangePasswordSerializer, ProfileSerializer,
)
from notifications.services import create_notification
from notifications.tasks import send_verification_email_task, send_password_reset_email_task

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        user.email_verification_token = f'{uid}/{token}'
        user.save(update_fields=['email_verification_token'])

        send_verification_email_task.delay(user.id, uid, token)
        create_notification(
            user=user,
            notification_type='email_verification',
            title='Verify your email',
            message='Please check your inbox to verify your email address.',
        )

        return Response(
            {'message': 'Registration successful. Please verify your email.'},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]


class TokenRefreshView(TokenRefreshView):
    pass


class VerifyEmailView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid link.'}, status=status.HTTP_400_BAD_REQUEST)

        if default_token_generator.check_token(user, token):
            user.is_email_verified = True
            user.email_verification_token = ''
            user.save(update_fields=['is_email_verified', 'email_verification_token'])
            create_notification(
                user=user,
                notification_type='email_verification',
                title='Email verified',
                message='Your email has been successfully verified.',
            )
            return Response({'message': 'Email verified successfully.'})

        return Response({'error': 'Invalid or expired link.'}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = (AllowAny,)
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If the email exists, a reset link has been sent.'})

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        send_password_reset_email_task.delay(user.id, uid, token)
        create_notification(
            user=user,
            notification_type='password_reset',
            title='Password reset requested',
            message='A password reset link has been sent to your email.',
        )
        return Response({'message': 'If the email exists, a reset link has been sent.'})


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            uid = force_str(urlsafe_base64_decode(request.data.get('uidb64', '')))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, serializer.validated_data['token']):
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['password'])
        user.save()
        create_notification(
            user=user,
            notification_type='password_reset',
            title='Password changed',
            message='Your password has been successfully changed.',
        )
        return Response({'message': 'Password reset successful.'})


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Wrong password.'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'message': 'Password changed successfully.'})


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, IsAdmin)
    filterset_fields = ('role', 'is_email_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering_fields = ('email', 'date_joined', 'first_name', 'last_name')
    ordering = ('-date_joined',)

from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.permissions import IsPortalManagerOrReadOnly
from apps.common.request import body_str
from apps.common.scope import can_use_portal, owner_of
from apps.common.throttle import LOGIN_LIMITER

from .models import User
from .serializers import MeSerializer, StaffSerializer


def tokens_for(user):
    r = RefreshToken.for_user(user)
    return {'access': str(r.access_token), 'refresh': str(r)}


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Portal login: email (or mobile) + password."""
    ident = str(request.data.get('identifier') or request.data.get('email') or '').strip()
    password = str(request.data.get('password') or '')
    LOGIN_LIMITER.check(ident.lower())           # locked after 10 wrong passwords, even if the next one is right
    user = User.objects.filter(email__iexact=ident).first() or User.objects.filter(mobile=ident).first() if ident else None
    user = authenticate(request, email=user.email, password=password) if user else None
    if not user or not user.is_active:
        LOGIN_LIMITER.fail(ident.lower())
        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
    LOGIN_LIMITER.reset(ident.lower())
    if not can_use_portal(user):
        return Response({'detail': 'Your role cannot access the portal. Use the POS.'}, status=status.HTTP_403_FORBIDDEN)
    return Response({**tokens_for(user), 'user': MeSerializer(user).data})


@api_view(['GET', 'PATCH'])
def me(request):
    if request.method == 'PATCH':
        for f in ('name', 'mobile', 'is_2fa_enabled'):
            if f in request.data:
                setattr(request.user, f, request.data[f])
        request.user.save()
    return Response(MeSerializer(request.user).data)


@api_view(['POST'])
def change_password(request):
    old, new = body_str(request, 'old_password'), body_str(request, 'new_password')
    if not request.user.check_password(old):
        return Response({'detail': 'Current password is wrong.'}, status=400)
    if len(new) < 8:
        return Response({'detail': 'New password must be at least 8 characters.'}, status=400)
    request.user.set_password(new)
    request.user.save()
    return Response({'detail': 'Password changed.'})


class StaffViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsPortalManagerOrReadOnly]

    def get_queryset(self):
        return User.objects.filter(owner=owner_of(self.request.user), is_owner=False).order_by('name')

    def perform_destroy(self, instance):
        instance.is_active = False   # keep history on old bills
        instance.save()
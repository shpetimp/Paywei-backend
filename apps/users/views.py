from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, timedelta
from django.db.models import Sum
from .serializers import (
    APIKeySerializer,
    UserSerializer,
    WhitelistAddressSerializer
)
from .models import CustomUser as User, APIKey, WhitelistAddress
from rest_framework import viewsets
from .permissions import IsOwner
from django.utils import timezone
from rest_framework.decorators import action
from django_filters import rest_framework as filters


# Create your views here.

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    model = User
    permission_classes = (IsOwner,)
    queryset = User.objects.all()
    serializer_class = UserSerializer


class APIKeyViewSet(viewsets.ModelViewSet):
    model = APIKey
    permission_classes = (IsOwner,)
    serializer_class = APIKeySerializer

    def get(self, request, format=None):
        if not self.request.user.is_authenticated:
            return Response({'error': 'You are not logged in'}, status=401)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return APIKey.objects.none()
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    

class WhitelistAddressViewSet(viewsets.ModelViewSet):
    model = WhitelistAddress
    permission_classes = (IsOwner,)
    serializer_class = WhitelistAddressSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('status',)

    def get(self, request, format=None):
        if not self.request.user.is_authenticated:
            return Response({'error': 'You are not logged in'}, status=401)
    
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return WhitelistAddress.objects.none()
        return WhitelistAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if not instance.archived_at:
            instance.archived_at = timezone.now()
            instance.status = WhitelistAddress.AddressStatus.archived
        instance.save()
        return instance

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        instance = self.get_object()
        yesterday = timezone.now() - timedelta(days=1)
        if self.request.data['secret'] != instance.secret or instance.created_at < yesterday:
            return Response({'error': 'unable to verify this address'})
        instance.status = WhitelistAddress.AddressStatus.verified
        instance.save()
        return Response(self.serializer_class(instance).data)
    
    
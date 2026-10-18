from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('logs', views.AuditLogViewSet, basename='log')

urlpatterns = [path('audit/', include(router.urls))]
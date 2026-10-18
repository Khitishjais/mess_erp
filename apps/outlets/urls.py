from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('outlets', views.OutletViewSet, basename='outlet')
router.register('zones', views.ZoneViewSet, basename='zone')
router.register('devices', views.DeviceViewSet, basename='device')

urlpatterns = [
    path('pos/activate/', views.activate_device),
    path('', include(router.urls)),
]
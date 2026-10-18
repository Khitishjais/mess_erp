from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import pos, views

router = DefaultRouter()
router.register('orders', views.OrderViewSet, basename='order')
router.register('kots', views.KotViewSet, basename='kot')

urlpatterns = [
    path('orders/live/', views.live_orders),
    path('pos/staff/', pos.pos_staff),
    path('pos/login/', pos.pos_login),
    path('pos/bootstrap/', pos.bootstrap),
    path('pos/changes/', pos.changes),
    path('sync/orders/', pos.sync_orders),
    path('pos/shifts/', pos.shift_open),
    path('pos/shifts/<int:pk>/close/', pos.shift_close),
    path('', include(router.urls)),
]
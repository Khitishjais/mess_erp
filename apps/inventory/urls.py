from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('materials', views.RawMaterialViewSet, basename='material')
router.register('ledger', views.StockLedgerViewSet, basename='ledger')
router.register('purchase-orders', views.PurchaseOrderViewSet, basename='po')

urlpatterns = [
    path('inventory/invoice/scan/', views.invoice_scan),
    path('inventory/invoice/review/', views.invoice_review),
    path('inventory/invoice/apply/', views.invoice_apply),
    path('inventory/stock-summary/', views.stock_summary),
    path('inventory/closing-tracker/', views.closing_tracker),
    path('inventory/pending-purchases/', views.pending_purchases),
    path('inventory/', include(router.urls)),
]
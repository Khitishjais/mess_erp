from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('feedback', views.FeedbackViewSet, basename='feedback')

urlpatterns = [
    path('ai/anomalies/', views.anomalies),
    path('ai/pricing/', views.pricing),
    path('ai/kitchen-eta/', views.kitchen_eta),
    path('ai/chat/', views.chat),
    path('ai/agent/', views.agent),
    path('ai/invoice-scan/', views.invoice_scan),
    path('ai/describe/', views.describe),
    path('ai/feedback-summary/', views.feedback_summary),
    path('ai/', include(router.urls)),
]
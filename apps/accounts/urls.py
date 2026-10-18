from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register('staff', views.StaffViewSet, basename='staff')

urlpatterns = [
    path('auth/login/', views.login),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('me/', views.me),
    path('me/password/', views.change_password),
    path('', include(router.urls)),
]
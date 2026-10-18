from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('taxes', views.TaxViewSet, basename='tax')
router.register('categories', views.CategoryViewSet, basename='category')
router.register('tags', views.TagViewSet, basename='tag')
router.register('addons', views.AddonViewSet, basename='addon')
router.register('items', views.ItemViewSet, basename='item')
router.register('tables', views.DiningTableViewSet, basename='table')
router.register('item-status', views.ItemStatusViewSet, basename='item-status')

urlpatterns = [path('', include(router.urls))]
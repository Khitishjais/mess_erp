from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('settings', views.SettingViewSet, basename='mess-setting')
router.register('special-days', views.SpecialDayViewSet, basename='mess-special')
router.register('recipes', views.RecipeViewSet, basename='recipe')
router.register('meal-plan', views.MealPlanViewSet, basename='mealplan')
router.register('attendance', views.AttendanceViewSet, basename='attendance')
router.register('wastage', views.WastageViewSet, basename='wastage')

urlpatterns = [
    path('mess/weekly-menu/', views.weekly_menu),
    path('mess/forecast/', views.forecast),
    path('mess/plan/', views.plan),
    path('mess/purchases/', views.purchases),
    path('mess/purchase-draft/', views.purchase_draft),
    path('mess/alerts/', views.alerts),
    path('mess/wastage-insights/', views.wastage_report),
    path('mess/menu-engineering/', views.menu_eng),
    path('mess/automation/run/', views.automation_run),
    path('mess/automation/cron/', views.automation_cron),
    path('mess/automation/status/', views.automation_status),
    path('mess/daily-plan/', views.daily_plan),
    path('mess/daily-report/', views.daily_report),
    path('mess/', include(router.urls)),
]
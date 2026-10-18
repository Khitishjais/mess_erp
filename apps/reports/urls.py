from django.urls import path

from . import dashboard, views

urlpatterns = [
    path('dashboard/kpis/', dashboard.kpis),
    path('dashboard/outlet-stats/', dashboard.outlet_stats),
    path('dashboard/taxes/', dashboard.taxes),
    path('dashboard/discounts/', dashboard.discounts),
    path('reports/', views.report_list),
    path('reports/<str:code>/favorite/', views.toggle_favorite),
    path('reports/<str:code>/data/', views.report_data),
]
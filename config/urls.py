"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.outlets.urls')),
    path('api/v1/', include('apps.catalog.urls')),
    path('api/v1/', include('apps.orders.urls')),
    path('api/v1/', include('apps.reports.urls')),
    path('api/v1/', include('apps.inventory.urls')),
    path('api/v1/', include('apps.audit.urls')),
    path('api/v1/', include('apps.mess.urls')),
    path('api/v1/', include('apps.ai.urls')),
    path('api/v1/', include('apps.prefs.urls')),
]

if settings.DEBUG:               # the Django admin is a development tool; it is not exposed on a hosted server
    urlpatterns.insert(0, path('admin/', admin.site.urls))

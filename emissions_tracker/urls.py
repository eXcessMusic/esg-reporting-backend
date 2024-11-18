from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from emissions.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('emissions.urls')),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', RedirectView.as_view(url='/dashboard/', permanent=True), name='index'),
]
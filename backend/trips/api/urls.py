from django.urls import path

from trips.api.views import AnalyzeView, GeocodeView, HealthView

urlpatterns = [
    path("analyze", AnalyzeView.as_view()),
    path("geocode", GeocodeView.as_view()),
    path("health", HealthView.as_view()),
]

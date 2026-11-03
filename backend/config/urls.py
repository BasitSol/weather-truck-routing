from django.urls import include, path, re_path

from trips.api.views import spa_index

urlpatterns = [
    path("api/v1/", include("trips.api.urls")),
    re_path(r"^(?!api/).*$", spa_index),
]

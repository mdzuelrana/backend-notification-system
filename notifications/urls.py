from django.urls import path
from .views import NotificationListCreateView, NotificationDetailView, NotificationRetryView, NotificationStatsView

app_name = "notifications"

urlpatterns = [
    path("",              NotificationListCreateView.as_view(), name="list-create"),
    path("stats/",        NotificationStatsView.as_view(),      name="stats"),
    path("<uuid:pk>/",    NotificationDetailView.as_view(),     name="detail"),
    path("<uuid:pk>/retry/", NotificationRetryView.as_view(),   name="retry"),
]
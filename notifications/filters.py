import django_filters
from .models import Notification, NotificationStatus

class NotificationFilter(django_filters.FilterSet):
    status           = django_filters.ChoiceFilter(choices=NotificationStatus.choices)
    scheduled_after  = django_filters.DateTimeFilter(field_name="scheduled_time", lookup_expr="gte")
    scheduled_before = django_filters.DateTimeFilter(field_name="scheduled_time", lookup_expr="lte")
    created_after    = django_filters.DateTimeFilter(field_name="created_at",     lookup_expr="gte")

    class Meta:
        model  = Notification
        fields = ["status", "scheduled_after", "scheduled_before", "created_after"]
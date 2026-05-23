from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from .models import Notification, NotificationStatus

class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ("id", "title", "message", "scheduled_time")
        read_only_fields = ("id",)

    def validate_scheduled_time(self, value):
        grace = timezone.timedelta(seconds=5)
        if value < timezone.now() - grace:
            raise serializers.ValidationError(
                "Scheduled time cannot be in the past. Please provide a future datetime (UTC).")
        return value

class NotificationSerializer(serializers.ModelSerializer):
    max_retries = serializers.SerializerMethodField()
    can_retry   = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Notification
        fields = ("id", "title", "message", "scheduled_time", "status",
                  "retry_count", "max_retries", "can_retry", "celery_task_id",
                  "last_attempted_at", "sent_at", "failure_reason", "created_at", "updated_at")
        read_only_fields = fields

    def get_max_retries(self, obj):
        return getattr(settings, "MAX_RETRY_COUNT", 3)

class NotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ("title", "message", "scheduled_time")

    def validate_scheduled_time(self, value):
        if value < timezone.now() - timezone.timedelta(seconds=5):
            raise serializers.ValidationError("Scheduled time cannot be in the past.")
        return value

    def validate(self, attrs):
        if self.instance.status not in (NotificationStatus.PENDING,):
            raise serializers.ValidationError(
                f"Only PENDING notifications can be edited (current: {self.instance.status}).")
        return attrs
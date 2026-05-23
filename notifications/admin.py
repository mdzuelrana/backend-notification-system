from django.contrib import admin
from django.utils.html import format_html
from .models import Notification, NotificationStatus

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("title", "user", "status_badge", "retry_count", "scheduled_time", "sent_at", "created_at")
    list_filter   = ("status",)
    search_fields = ("title", "message", "user__email")
    readonly_fields = ("id", "celery_task_id", "last_attempted_at", "sent_at",
                       "failure_reason", "created_at", "updated_at")
    ordering = ("-created_at",)

    def status_badge(self, obj):
        colors = {
            NotificationStatus.PENDING:            "#f59e0b",
            NotificationStatus.PROCESSING:         "#3b82f6",
            NotificationStatus.SENT:               "#10b981",
            NotificationStatus.FAILED:             "#ef4444",
            NotificationStatus.PERMANENTLY_FAILED: "#7f1d1d",
            NotificationStatus.CANCELLED:          "#6b7280",
        }
        return format_html('<span style="color:{}; font-weight:600">{}</span>',
            colors.get(obj.status, "#6b7280"), obj.get_status_display())
    status_badge.short_description = "Status"
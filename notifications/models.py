import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class NotificationStatus(models.TextChoices):
    PENDING            = "pending",            "Pending"
    PROCESSING         = "processing",         "Processing"
    SENT               = "sent",               "Sent"
    FAILED             = "failed",             "Failed"
    PERMANENTLY_FAILED = "permanently_failed", "Permanently Failed"
    CANCELLED          = "cancelled",          "Cancelled"

class Notification(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title          = models.CharField(max_length=255)
    message        = models.TextField()
    scheduled_time = models.DateTimeField(db_index=True)
    status         = models.CharField(max_length=20, choices=NotificationStatus.choices,
                                      default=NotificationStatus.PENDING, db_index=True)
    retry_count        = models.PositiveSmallIntegerField(default=0)
    celery_task_id     = models.CharField(max_length=255, blank=True, null=True)
    last_attempted_at  = models.DateTimeField(null=True, blank=True)
    sent_at            = models.DateTimeField(null=True, blank=True)
    failure_reason     = models.TextField(blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["scheduled_time", "status"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title} — {self.user}"

    @property
    def max_retries(self):
        return getattr(settings, "MAX_RETRY_COUNT", 3)

    @property
    def can_retry(self):
        return self.status == NotificationStatus.FAILED and self.retry_count < self.max_retries

    def mark_processing(self, task_id=None):
        self.status = NotificationStatus.PROCESSING
        self.last_attempted_at = timezone.now()
        if task_id:
            self.celery_task_id = task_id
        self.save(update_fields=["status", "last_attempted_at", "celery_task_id", "updated_at"])

    def mark_sent(self):
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def mark_failed(self, reason=""):
        self.retry_count += 1
        self.failure_reason = reason
        if self.retry_count >= self.max_retries:
            self.status = NotificationStatus.PERMANENTLY_FAILED
        else:
            self.status = NotificationStatus.FAILED
        self.save(update_fields=["status", "retry_count", "failure_reason", "updated_at"])

    def reset_for_retry(self):
        if not self.can_retry:
            raise ValueError(f"Notification {self.id} cannot be retried.")
        self.status = NotificationStatus.PENDING
        self.save(update_fields=["status", "updated_at"])
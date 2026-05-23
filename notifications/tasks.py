import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("celery.task")

MAX_RETRY_COUNT    = getattr(settings, "MAX_RETRY_COUNT", 3)
RETRY_DELAY_SECONDS = getattr(settings, "RETRY_DELAY_SECONDS", 60)

@shared_task(bind=True, name="notifications.send_notification",
             max_retries=0, acks_late=True, reject_on_worker_lost=True)
def send_notification(self, notification_id):
    from notifications.models import Notification, NotificationStatus

    try:
        notification = Notification.objects.select_for_update().get(id=notification_id)
    except Notification.DoesNotExist:
        logger.error("Notification %s not found.", notification_id)
        return {"status": "not_found"}

    # Idempotency guard
    if notification.status in (NotificationStatus.SENT,
                                NotificationStatus.PERMANENTLY_FAILED,
                                NotificationStatus.CANCELLED):
        return {"status": "skipped", "reason": notification.status}

    notification.mark_processing(task_id=self.request.id)

    try:
        _dispatch(notification)
        notification.mark_sent()
        logger.info("Notification %s sent.", notification_id)
        return {"status": "sent"}

    except Exception as exc:
        reason = str(exc)
        notification.mark_failed(reason=reason)

        if notification.can_retry:
            backoff = RETRY_DELAY_SECONDS * (2 ** notification.retry_count)
            send_notification.apply_async(args=[notification_id], countdown=backoff)
            logger.warning("Retry scheduled in %ds for %s", backoff, notification_id)
        else:
            logger.error("Permanently failed: %s", notification_id)

        return {"status": "failed", "retry_count": notification.retry_count}

def _dispatch(notification):
    """
    Replace this with real delivery: email (SendGrid/SES),
    push (FCM/APNs), SMS (Twilio), etc.
    Raises exception to simulate 20% failure rate for demo.
    """
    import random
    if random.random() < 0.2:
        raise RuntimeError("Simulated delivery failure.")
    logger.debug("Delivered: %s to user %s", notification.id, notification.user_id)

@shared_task(name="notifications.process_pending_notifications")
def process_pending_notifications():
    """Periodic task: sweep due PENDING notifications every minute."""
    from notifications.models import Notification, NotificationStatus

    now  = timezone.now()
    due  = Notification.objects.filter(
        status=NotificationStatus.PENDING,
        scheduled_time__lte=now,
    ).select_for_update(skip_locked=True)

    count = 0
    for notification in due:
        send_notification.apply_async(args=[str(notification.id)])
        count += 1

    logger.info("Enqueued %d notifications.", count)
    return {"enqueued": count}
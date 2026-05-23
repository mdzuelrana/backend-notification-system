import os
from celery import Celery
from celery.signals import task_failure, task_retry, task_success
import logging

logger = logging.getLogger("celery")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("notifyflow")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    logger.error("Task FAILED | task_id=%s | task=%s | error=%s",
        task_id, sender.name if sender else "unknown", str(exception))

@task_retry.connect
def on_task_retry(sender=None, reason=None, **kwargs):
    logger.warning("Task RETRY | task=%s | reason=%s",
        sender.name if sender else "unknown", str(reason))

@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    logger.info("Task SUCCESS | task=%s | result=%s",
        sender.name if sender else "unknown", str(result))
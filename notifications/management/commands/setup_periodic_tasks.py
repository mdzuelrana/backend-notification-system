from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

class Command(BaseCommand):
    help = "Register Celery Beat periodic tasks."

    def handle(self, *args, **options):
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.MINUTES)

        task, created = PeriodicTask.objects.update_or_create(
            name="Process pending notifications",
            defaults={
                "task":    "notifications.process_pending_notifications",
                "interval": schedule,
                "args":    json.dumps([]),
                "enabled": True,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action}: {task.name}"))
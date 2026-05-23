import logging
from django.conf import settings
from django.utils import timezone
from rest_framework import status, generics, filters
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from .filters import NotificationFilter
from .models import Notification, NotificationStatus
from .serializers import NotificationCreateSerializer, NotificationSerializer, NotificationUpdateSerializer
from .tasks import send_notification

logger = logging.getLogger(__name__)

class NotificationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class    = NotificationFilter
    search_fields      = ["title", "message"]
    ordering_fields    = ["created_at", "scheduled_time", "status"]
    ordering           = ["-created_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return NotificationCreateSerializer if self.request.method == "POST" else NotificationSerializer

    def post(self, request, *args, **kwargs):
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = serializer.save(user=request.user)

        delay = max(0, (notification.scheduled_time - timezone.now()).total_seconds())
        task  = send_notification.apply_async(args=[str(notification.id)], countdown=delay)
        notification.celery_task_id = task.id
        notification.save(update_fields=["celery_task_id"])

        logger.info("Scheduled | id=%s | user=%s | delay=%.1fs",
            notification.id, request.user.email, delay)

        return Response({
            "success": True,
            "message": f"Notification scheduled in {delay:.0f}s.",
            "data": NotificationSerializer(notification).data,
        }, status=status.HTTP_201_CREATED)


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    http_method_names  = ["get", "patch", "delete"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return NotificationUpdateSerializer if self.request.method == "PATCH" else NotificationSerializer

    def retrieve(self, request, *args, **kwargs):
        notification = self.get_object()
        return Response({"success": True, "data": NotificationSerializer(notification).data})

    def partial_update(self, request, *args, **kwargs):
        notification = self.get_object()
        serializer   = NotificationUpdateSerializer(notification, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()

        delay = max(0, (notification.scheduled_time - timezone.now()).total_seconds())
        task  = send_notification.apply_async(args=[str(notification.id)], countdown=delay)
        notification.celery_task_id = task.id
        notification.save(update_fields=["celery_task_id"])

        return Response({"success": True, "data": NotificationSerializer(notification).data})

    def destroy(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.status not in (NotificationStatus.PENDING,):
            raise ValidationError(f"Only PENDING notifications can be cancelled (current: {notification.status}).")
        notification.status = NotificationStatus.CANCELLED
        notification.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "message": "Notification cancelled."})


class NotificationRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"success": False, "error": {"message": "Notification not found."}},
                status=status.HTTP_404_NOT_FOUND)

        if notification.status == NotificationStatus.PERMANENTLY_FAILED:
            return Response({"success": False, "error": {
                "message": f"Permanently failed after {notification.retry_count} attempts. Cannot retry."}},
                status=status.HTTP_409_CONFLICT)

        if notification.status != NotificationStatus.FAILED:
            return Response({"success": False, "error": {
                "message": f"Only FAILED notifications can be retried (current: {notification.status})."}},
                status=status.HTTP_409_CONFLICT)

        if not notification.can_retry:
            return Response({"success": False, "error": {
                "message": f"Max retry limit ({notification.max_retries}) reached."}},
                status=status.HTTP_409_CONFLICT)

        notification.reset_for_retry()
        task = send_notification.apply_async(args=[str(notification.id)])
        notification.celery_task_id = task.id
        notification.save(update_fields=["celery_task_id"])

        logger.info("Manual retry | id=%s | user=%s", notification.id, request.user.email)

        return Response({"success": True, "message": "Queued for retry.",
            "data": NotificationSerializer(notification).data}, status=status.HTTP_202_ACCEPTED)


class NotificationStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        qs     = Notification.objects.filter(user=request.user)
        totals = qs.values("status").annotate(count=Count("id"))
        stats  = {row["status"]: row["count"] for row in totals}
        return Response({"success": True, "data": {"total": qs.count(), "by_status": stats}})
    

def home(request):
    return JsonResponse({"message": "API is running"})

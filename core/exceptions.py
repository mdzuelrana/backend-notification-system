import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "success": False,
            "error": {
                "code": _resolve_code(response.status_code),
                "message": _resolve_message(response.data, response.status_code),
            },
        }
        if isinstance(response.data, dict) and any(
            isinstance(v, list) for v in response.data.values()
        ):
            error_payload["error"]["details"] = response.data

        response.data = error_payload

        if response.status_code >= 500:
            logger.error("Server error | status=%s | path=%s | error=%s",
                response.status_code, context["request"].path, str(exc))

    return response

def _resolve_code(status_code):
    codes = {
        400: "bad_request", 401: "unauthorized", 403: "forbidden",
        404: "not_found", 405: "method_not_allowed", 409: "conflict",
        429: "rate_limit_exceeded", 500: "internal_server_error",
    }
    return codes.get(status_code, "error")

def _resolve_message(data, status_code):
    if isinstance(data, dict):
        if "detail" in data:
            detail = data["detail"]
            return str(detail) if not isinstance(detail, list) else detail[0]
        for key, val in data.items():
            if isinstance(val, list) and val:
                return f"{key}: {val[0]}"
    if isinstance(data, list) and data:
        return str(data[0])
    return "An error occurred."
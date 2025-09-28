import json
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from rest_framework import status

from core.helpers.api_response import APIResponse


class ExceptionMiddleware:
    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        self.logger = logging.getLogger("api")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if not isinstance(response, HttpResponseBase):
            response = HttpResponse(
                content=json.dumps(response),
                content_type="application/json",
                status=200,
            )

        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:
        request_id = getattr(request, "request_id", None)
        self.logger.error(
            "unhandled_exception",
            extra={
                "event": "unhandled_exception",
                "request_id": str(request_id) if request_id else None,
                "path": getattr(request, "path", None),
                "exception": str(exception),
            },
            exc_info=True,
        )

        # Add status_code attribute to exception if it doesn't exist
        if not hasattr(exception, "status_code"):
            print("Exception does not have status code")
            exception.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR  # type: ignore

        response = APIResponse(success=False, status_code=getattr(exception, "status_code", 500), error=exception).response()
        # add request id to error response header as well
        try:
            header_name = getattr(settings, "REQUEST_ID_HEADER", "X-Request-ID")
            if request_id:
                response[header_name] = str(request_id)
        except Exception:
            pass
        return response

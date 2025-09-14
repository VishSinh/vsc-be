import json
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from rest_framework import status

from core.helpers.api_response import APIResponse


class ExceptionMiddleware:
    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

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
        print(str(exception))

        # Add status_code attribute to exception if it doesn't exist
        if not hasattr(exception, "status_code"):
            print("Exception does not have status code")
            setattr(exception, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)

        return APIResponse(success=False, status_code=getattr(exception, "status_code", 500), error=exception).response()

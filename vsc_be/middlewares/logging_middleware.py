import json
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.utils import timezone


class LoggingMiddleware:
    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Log incoming request
        self._log_request(request)

        # Get response
        response = self.get_response(request)

        # Log outgoing response
        self._log_response(request, response)

        return response

    def _log_request(self, request: HttpRequest) -> None:
        """Log incoming request details"""
        timestamp = timezone.now().isoformat()

        # Get request body
        body = ""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = request.body.decode("utf-8")
                # Try to parse as JSON for better formatting
                try:
                    body = json.dumps(json.loads(body), indent=2)
                except json.JSONDecodeError:
                    pass
            except UnicodeDecodeError:
                body = "<binary data>"

        # Get headers (excluding sensitive ones)
        headers = dict(request.headers)
        sensitive_headers = ["authorization", "cookie", "x-csrftoken"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "***REDACTED***"

        # Handle body parsing safely
        body_data = None
        if body:
            try:
                body_data = json.loads(body)
            except json.JSONDecodeError:
                body_data = body  # Keep as string if not valid JSON

        log_data = {
            "timestamp": timestamp,
            "method": request.method,
            "path": request.path,
            "query_params": dict(request.GET),
            "headers": headers,
            "body": body_data,
        }

        print(f"📥 INCOMING REQUEST:\n{json.dumps(log_data, indent=2)}")

    def _log_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """Log outgoing response details"""
        timestamp = timezone.now().isoformat()

        # Get response body
        body = ""
        if hasattr(response, "content"):
            try:
                body = response.content.decode("utf-8")
                # Try to parse as JSON for better formatting
                try:
                    body = json.dumps(json.loads(body), indent=2)
                except json.JSONDecodeError:
                    pass
            except UnicodeDecodeError:
                body = "<binary data>"

        # Get headers
        headers = dict(response.headers)

        # Handle body parsing safely
        body_data = None
        if body:
            try:
                body_data = json.loads(body)
            except json.JSONDecodeError:
                body_data = body  # Keep as string if not valid JSON

        log_data = {
            "timestamp": timestamp,
            "status_code": response.status_code,
            "headers": headers,
            "body": body_data,
        }

        print(f"📤 OUTGOING RESPONSE:\n{json.dumps(log_data, indent=2)}")

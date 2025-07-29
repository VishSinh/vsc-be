from typing import Any, Dict, Optional

from django.http import JsonResponse


class APIResponse:
    def __init__(
        self,
        success: bool = True,
        status_code: int = 200,
        data: Optional[Any] = None,
        pagination: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ):
        self.success = success
        self.status_code = status_code
        self.data = data if data is not None else {}
        self.pagination = pagination if pagination is not None else {}
        self.error = error

    def _format_error(self) -> Dict[str, str]:
        if not self.error:
            return {"code": "", "message": "", "details": ""}

        return {
            "code": self.error.__class__.__name__,
            "message": getattr(self.error, "message", "An error occurred"),
            "details": getattr(self.error, "details", str(self.error)),
        }

    def response(self) -> JsonResponse:
        response_data: Dict[str, Any] = {
            "success": self.success,
        }

        if self.data is not None:
            response_data["data"] = self.data

        if self.error is not None:
            response_data["error"] = self._format_error()

        if self.pagination is not None:
            response_data["pagination"] = self.pagination

        return JsonResponse(response_data, status=self.status_code)

    def __str__(self) -> str:
        return f"APIResponse(success={self.success}, status_code={self.status_code}, data={self.data}, error={self.error})"

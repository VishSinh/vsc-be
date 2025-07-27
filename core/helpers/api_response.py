from typing import Optional, Any, Dict
from django.http import JsonResponse


class APIResponse:
    def __init__(self, success: bool = True, status_code: int = 200, data: Optional[Any] = None, error: Optional[Exception] = None):
        self.success = success
        self.status_code = status_code
        self.data = data if data is not None else {}
        self.error = error

    def _format_error(self) -> Dict[str, str]:
        if not self.error:
            return {"code": "", "message": "", "details": ""}
        
        return {"code": self.error.__class__.__name__, "message": getattr(self.error, "message", "An error occurred"), "details": getattr(self.error, "details", str(self.error))}

    def response(self, correlation_id: Optional[str] = None) -> JsonResponse:
        response_data = {"success": self.success, "data": self.data, "error": self._format_error()}

        if correlation_id:
            response_data["correlation_id"] = correlation_id

        return JsonResponse(response_data, status=self.status_code)

    def __str__(self) -> str: 
        return f"APIResponse(success={self.success}, status_code={self.status_code}, data={self.data}, error={self.error})"


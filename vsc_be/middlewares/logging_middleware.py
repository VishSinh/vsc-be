import json
import logging
import time
import uuid
from typing import Any, Dict, Optional, Union

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from auditing.models import APIAuditLog
from core.metrics import REQUEST_COUNTER, REQUEST_INFLIGHT


class LoggingMiddleware:
    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        self.logger = logging.getLogger("api")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        enable_console = getattr(settings, "ENABLE_API_LOGGING", False)
        enable_db = getattr(settings, "ENABLE_API_DB_AUDIT", None)
        if enable_db is None:
            enable_db = enable_console
        request_id = uuid.uuid4()
        start = time.monotonic()
        # attach request id for downstream logging and response header
        setattr(request, "request_id", request_id)
        skip_internal = self._should_skip_audit(request)
        if enable_console and not skip_internal:
            self._log_request(request, request_id)

        # Increment inflight
        try:
            REQUEST_INFLIGHT.inc()
        except Exception:
            pass
        # Get response
        response = self.get_response(request)

        # add request id header
        try:
            header_name = getattr(settings, "REQUEST_ID_HEADER", "X-Request-ID")
            response[header_name] = str(request_id)
        except Exception:
            pass

        if enable_console and not skip_internal:
            # include duration_ms in response log for easier Loki filtering
            try:
                duration_ms = int((time.monotonic() - start) * 1000)
            except Exception:
                duration_ms = None
            self._log_response(request, response, request_id, duration_ms)
        if enable_db and not self._should_skip_audit(request):
            try:
                duration_ms = int((time.monotonic() - start) * 1000)
                self._persist_api_audit(request, response, request_id, duration_ms)
            except Exception:
                pass

        # Decrement inflight and increment request counter
        try:
            REQUEST_INFLIGHT.dec()
            if not skip_internal:
                status = getattr(response, "status_code", None)
                REQUEST_COUNTER.labels(method=request.method, path=request.path, status=str(status)).inc()
        except Exception:
            pass

        return response

    def _log_request(self, request: HttpRequest, request_id: uuid.UUID) -> None:
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

        self.logger.info("incoming_request", extra={"event": "incoming_request", "request_id": str(request_id), **log_data})

    def _log_response(self, request: HttpRequest, response: HttpResponse, request_id: uuid.UUID, duration_ms: Optional[int] = None) -> None:
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

        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms

        self.logger.info(
            "outgoing_response",
            extra={
                "event": "outgoing_response",
                "request_id": str(request_id),
                "path": getattr(request, "path", ""),
                **log_data,
            },
        )

    def _persist_api_audit(self, request: HttpRequest, response: HttpResponse, request_id: uuid.UUID, duration_ms: int) -> None:
        redacted_keys = set(getattr(settings, "AUDIT_REDACTED_FIELDS", ["password", "token", "authorization", "cookie", "secret", "api_key"]))
        max_body_chars = int(getattr(settings, "AUDIT_MAX_BODY_CHARS", 4096))
        staff = getattr(request, "staff", None)

        def _client_ip(req: HttpRequest) -> Optional[str]:
            xff = req.META.get("HTTP_X_FORWARDED_FOR")
            if xff:
                parts = [p.strip() for p in xff.split(",") if p.strip()]
                if parts:
                    return str(parts[0])
            ra = req.META.get("REMOTE_ADDR")
            return str(ra) if isinstance(ra, str) else None

        def _redact(obj: Union[Dict[str, Any], list, str, int, float, None]) -> Union[Dict[str, Any], list, str, int, float, None]:
            if isinstance(obj, dict):
                return {k: ("***REDACTED***" if k.lower() in redacted_keys else _redact(v)) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_redact(v) for v in obj]
            return obj

        def _parse_body(raw: Optional[str]) -> Union[Dict[str, Any], list, str, None]:
            if not raw:
                return {}
            try:
                parsed = _redact(json.loads(raw))
                if isinstance(parsed, (dict, list, str)):
                    return parsed
                return str(parsed) if parsed is not None else {}
            except Exception:
                s = raw if raw is not None and len(raw) <= max_body_chars else (raw[:max_body_chars] if raw is not None else "")
                return s

        def _request_body(req: HttpRequest) -> Union[Dict[str, Any], list, str, None]:
            if req.method in ["POST", "PUT", "PATCH"]:
                try:
                    return _parse_body(req.body.decode("utf-8"))
                except Exception:
                    return "<binary or unreadable>"
            return {}

        def _response_body(resp: HttpResponse) -> Union[Dict[str, Any], list, str, None]:
            if hasattr(resp, "content"):
                try:
                    return _parse_body(resp.content.decode("utf-8"))
                except Exception:
                    return "<binary or unreadable>"
            return {}

        def _sanitize_headers(h: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for k, v in h.items():
                if k.lower() in {"authorization", "cookie", "x-csrftoken"}:
                    result[k] = "***REDACTED***"
                else:
                    result[k] = v
            return result

        try:
            content_len = None
            if hasattr(response, "content"):
                try:
                    content_len = len(response.content)
                except Exception:
                    content_len = None
            if content_len is None:
                try:
                    content_len = int(response.headers.get("Content-Length", "")) if hasattr(response, "headers") else None
                except Exception:
                    content_len = None
            APIAuditLog.objects.create(
                id=uuid.uuid4(),
                staff=staff if staff else None,
                endpoint=request.path,
                request_method=request.method,
                request_body=_request_body(request),
                response_body=_response_body(response),
                status_code=getattr(response, "status_code", None),
                duration_ms=duration_ms,
                ip_address=_client_ip(request),
                user_agent=request.headers.get("User-Agent", ""),
                query_params=dict(request.GET or {}),
                headers=_sanitize_headers(dict(request.headers)),
                request_id=request_id,
                response_size_bytes=content_len,
            )
        except Exception:
            pass

    def _should_skip_audit(self, request: HttpRequest) -> bool:
        # Skip CORS preflight and explicitly excluded paths
        if getattr(request, "method", "").upper() == "OPTIONS":
            return True
        excluded = getattr(settings, "AUDIT_EXCLUDED_PATHS", [])
        try:
            return any(p and p in request.path for p in excluded)
        except Exception:
            return False

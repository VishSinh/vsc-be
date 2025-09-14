from functools import wraps

from django.conf import settings

from core.helpers.api_response import APIResponse

"""
The `forge` decorator standardizes API responses for Django Rest Framework APIView methods.

Usage:
    - Wraps a view method to ensure all responses are returned as a consistent JSON structure using `APIResponse`.
    - Handles the following return types from the decorated view:
        1. `response_body`:
            - Returns: APIResponse with data=response_body.
        2. `(response_body, pagination_info)`:
            - If the second element is a dict, treats it as pagination info and returns APIResponse with data and pagination.
        3. `(response_body, status_code)`:
            - If the second element is not a dict, treats it as a status code and returns APIResponse with data and status_code.
        4. Exception:
            - If the view raises or returns an Exception, it is re-raised or wrapped in an error response.

Example:
    @forge
    def get(self, request):
        # return data only
        return {"foo": "bar"}

    @forge
    def get(self, request):
        # return data and pagination
        return [{"foo": "bar"}], {"page": 1, "total": 10}

    @forge
    def post(self, request):
        # return data and custom status code
        return {"created": True}, 201
"""


def _absolute_media_url(request, value):
    if not isinstance(value, str):
        return value
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/media/"):
        path = value
    elif value.startswith("media/"):
        path = f"/{value}"
    else:
        return value
    base = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/") or request.build_absolute_uri("/").rstrip("/")
    return f"{base}{path}"


def _absolutize_media_urls(request, data):
    if request is None:
        return data
    if isinstance(data, dict):
        return {
            k: _absolutize_media_urls(request, v)
            if isinstance(v, (dict, list))
            else (
                _absolute_media_url(request, v)
                if isinstance(v, str) and (k == "image" or k.endswith("_image") or v.startswith("/media/") or v.startswith("media/"))
                else v
            )
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_absolutize_media_urls(request, item) for item in data]
    return data


def forge(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if isinstance(result, Exception):
            raise result
        try:
            request = args[1] if len(args) > 1 else None
            if isinstance(result, tuple) and len(result) == 2:
                if isinstance(result[1], dict):
                    response_body, pagination_info = result
                    response_body = _absolutize_media_urls(request, response_body)
                    return APIResponse(data=response_body, pagination=pagination_info).response()

                response_body, status_code = result
                response_body = _absolutize_media_urls(request, response_body)
                return APIResponse(data=response_body, status_code=status_code).response()

            data = _absolutize_media_urls(request, result)
            return APIResponse(data=data).response()

        except Exception as e:
            return APIResponse(success=False, status_code=500, error=e).response()

    return wrapper

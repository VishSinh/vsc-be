from functools import wraps

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


def forge(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if isinstance(result, Exception):
            raise result
        try:
            if isinstance(result, tuple) and len(result) == 2:
                if isinstance(result[1], dict):
                    response_body, pagination_info = result
                    return APIResponse(data=response_body, pagination=pagination_info).response()

                response_body, status_code = result
                return APIResponse(data=response_body, status_code=status_code).response()

            return APIResponse(data=result).response()

        except Exception as e:
            return APIResponse(success=False, status_code=500, error=e).response()

    return wrapper

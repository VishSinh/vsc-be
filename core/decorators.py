from functools import wraps

from core.helpers.api_response import APIResponse




def forge(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
            
        if isinstance(result, Exception):
            raise result
        try:
            if isinstance(result, tuple) and len(result) == 2:
                response_body, status_code = result
                return APIResponse(data=response_body, status_code=status_code).response()
            
            return APIResponse(data=result).response()
        
        except Exception as e:
            return APIResponse(success=False, status_code=500, error=e).response()
    
    return wrapper

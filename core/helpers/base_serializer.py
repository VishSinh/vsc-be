import json
from typing import Any
from rest_framework import serializers
from core.exceptions import BadRequest


class BaseSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        """
        Override to_internal_value to provide custom error formatting.
        Converts validation errors to a flat list of error messages.
        """
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError as exc:
            error_messages = [
                f"{key} - {error}" if key != "non_field_errors" else error
                for key, errors in exc.detail.items()
                for error in errors
            ]
            raise BadRequest(json.dumps(error_messages))

    def get_value(self, key: str, default: Any = '') -> Any:
        """Get a value from validated_data with a default fallback."""
        return self.validated_data.get(key, default)
    
    def require_value(self, key: str) -> Any:
        """Get a required value from validated_data or raise ValidationError."""
        try:
            return self.validated_data[key]
        except KeyError:
            raise BadRequest(f'Missing required field: {key}')
        
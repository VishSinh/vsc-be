from rest_framework.exceptions import ValidationError

from core.helpers.base_serializer import BaseSerializer


class ParamSerializer(BaseSerializer):
    """Base serializer for validating query parameters with type safety"""

    def validate(self, attrs):
        """Override this method for custom validation logic"""
        return attrs

    @classmethod
    def validate_params(cls, request):
        """
        Validate query parameters using this serializer class.

        Args:
            request: Django request object

        Returns:
            Validated serializer instance with get_value() method

        Raises:
            ValidationError: If validation fails
        """
        serializer = cls(data=request.query_params.dict())

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        return serializer

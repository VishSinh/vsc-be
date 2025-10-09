from rest_framework import serializers

from analytics.constants import AnalyticsType
from core.helpers.param_serializer import ParamSerializer


class DetailedAnalyticsParams(ParamSerializer):
    type = serializers.ChoiceField(choices=AnalyticsType.choices, required=True)
    days = serializers.IntegerField(min_value=1, max_value=5, required=False, default=1)

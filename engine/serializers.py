from rest_framework import serializers
from engine.validators import get_execution_order
from .models import Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = [
            "id",
            "name",
            "definition",
            "cron",
            "is_active",
            "version",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
    def validate_definition(self, value):
        try:
            get_execution_order(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return value
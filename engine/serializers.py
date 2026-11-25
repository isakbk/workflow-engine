
from rest_framework import serializers
from engine.models import Workflow
from engine.definition import validate_definition, build_graph, find_cycle,validate_executors



class WorkflowSerializer(serializers.ModelSerializer):

    class Meta:
        model = Workflow
        fields = [
            'id',
            'name',
            'definition',
            'cron',
            'is_active',
            'version',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'version']

    def validate(self, attrs):
        # Definition request मा पठाइएको छैन भने validation skip गर्ने
        if 'definition' not in attrs:
            return attrs

        definition = attrs['definition']

        # Step 1: Shape validation
        errors = validate_definition(definition)
        execuation_error=validate_executors(definition)
        errors.extend(execuation_error)

        if errors:
            raise serializers.ValidationError({
                'definition': errors
            })

        # Step 2: Build graph only after shape validation
        graph = build_graph(definition)

        # Step 3: Cycle validation
        cycle = find_cycle(graph)

        if cycle:
            path = " -> ".join(cycle)

            raise serializers.ValidationError({
                'definition': [
                    f"Cycle detected: {path}"
                ]
            })

        return attrs

    def create(self, validated_data):
        # Every new workflow starts at version 1
        validated_data['version'] = 1

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Definition पठाइएको छ कि छैन?
        if 'definition' in validated_data:

            old_definition = instance.definition or {}
            new_definition = validated_data['definition']

            old_tasks = old_definition.get('tasks', [])

            # पुरानो definition मा task छ र definition फरक छ भने
            if old_tasks and old_definition != new_definition:
                instance.version += 1

        return super().update(instance, validated_data)

from engine.serializers import WorkflowSerializer
import pytest


def test_serializer_valid_data(db):
    name = "test_workflow"
    definition = {"start": "node1", "nodes": []}
    serializer = WorkflowSerializer(data={"name": name, "definition": definition})
    assert serializer.is_valid()


def test_serializer_missing_name_invalid(db):
    definition = {"start": "node1", "nodes": []}
    serializer = WorkflowSerializer(data={"definition": definition})
    assert not serializer.is_valid()


def test_serializer_duplicate_name_invalid(db):
    serializer = WorkflowSerializer(
        data={"name": "workflow", "definition": {"start": "node1", "nodes": []}}
    )
    assert serializer.is_valid()
    serializer.save()
    # Try to create another workflow with the same name
    serializer = WorkflowSerializer(
        data={"name": "workflow", "definition": {"start": "node1", "nodes": []}}
    )
    assert not serializer.is_valid()




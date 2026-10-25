from engine.serializers import WorkflowSerializer
import pytest


def test_serializer_valid_data(db):
    name = "test_workflow"
    definition = {"tasks": [{"name": "task1", "fn": "task1", "depends_on": []}]}
    serializer = WorkflowSerializer(data={"name": name, "definition": definition})
    assert serializer.is_valid()


def test_serializer_missing_name_invalid(db):
    definition = {"tasks": [{"name": "task1", "fn": "task1", "depends_on": []}]}
    serializer = WorkflowSerializer(data={"definition": definition})
    assert not serializer.is_valid()


def test_serializer_duplicate_name_invalid(db):
    serializer = WorkflowSerializer(
        data={
            "name": "workflow",
            "definition": {
                "tasks": [{"name": "task1", "fn": "task1", "depends_on": []}]
            },
        }
    )
    assert serializer.is_valid()
    serializer.save()
    # Try to create another workflow with the same name
    serializer = WorkflowSerializer(
        data={
            "name": "workflow",
            "definition": {
                "tasks": [{"name": "task1", "fn": "task1", "depends_on": []}]
            },
        }
    )
    assert not serializer.is_valid()


def test_serializer_rejects_cycle(db):
    definition = {
        "tasks": [
            {"name": "task1", "fn": "task1", "depends_on": ["task2"]},
            {"name": "task2", "fn": "task2", "depends_on": ["task1"]},
        ]
    }
    serializer = WorkflowSerializer(data={"name": "workflow", "definition": definition})
    assert not serializer.is_valid()


def test_serializer_rejects_duplicate_task_names(db):
    definition = {
        "tasks": [
            {"name": "task1", "fn": "task1", "depends_on": []},
            {"name": "task1", "fn": "task2", "depends_on": []},
        ]
    }
    serializer = WorkflowSerializer(data={"name": "workflow", "definition": definition})
    assert not serializer.is_valid()


# ५ task को सही sales report
def test_serializer_accepts_sales_report(db):
    definition = {
        "tasks": [
            {"name": "task1", "fn": "task1", "depends_on": []},
            {"name": "task2", "fn": "task2", "depends_on": ["task1"]},
            {"name": "task3", "fn": "task3", "depends_on": ["task2"]},
            {"name": "task4", "fn": "task4", "depends_on": ["task3"]},
            {"name": "task5", "fn": "task5", "depends_on": ["task4"]},
        ]
    }
    serializer = WorkflowSerializer(data={"name": "workflow", "definition": definition})
    assert serializer.is_valid()
    serializer.save()

from engine.validators import get_execution_order, WorkflowValidationError
import pytest


def test_linear_chain_order():
    # Example
    definition = {
        "tasks": [
            {"name": "close", "depends_on": []},
            {"name": "open", "depends_on": ["close"]},
            {"name": "check", "depends_on": ["open"]},
        ]
    }
    assert get_execution_order(definition) == ["close", "open", "check"]


# ५ task (download, clean, chart, table, email), हरेक task आफ्नो dependency पछि (order.index(...) ले तुलना)
def test_sales_report_order():
    definition = {
        "tasks": [
            {"name": "download", "depends_on": []},
            {"name": "clean", "depends_on": ["download"]},
            {"name": "chart", "depends_on": ["clean"]},
            {"name": "table", "depends_on": ["clean"]},
            {"name": "email", "depends_on": ["chart", "table"]},
        ]
    }
    assert get_execution_order(definition) == [
        "download",
        "clean",
        "chart",
        "table",
        "email",
    ]


# A ↔ B मा error
def test_simple_cycle_fails():
    definition = {
        "tasks": [
            {"name": "A", "depends_on": ["B"]},
            {"name": "B", "depends_on": ["A"]},
        ]
    }
    try:
        get_execution_order(definition)
        assert False, "Expected WorkflowValidationError for cycle"
    except WorkflowValidationError as e:
        assert "cycle" in str(e).lower()


# A → B → C → A मा error
def test_three_task_cycle_fails():
    definition = {
        "tasks": [
            {"name": "A", "depends_on": ["B"]},
            {"name": "B", "depends_on": ["C"]},
            {"name": "C", "depends_on": ["A"]},
        ]
    }
    try:
        get_execution_order(definition)
        assert False, "Expected WorkflowValidationError for cycle"
    except WorkflowValidationError as e:
        assert "cycle" in str(e).lower()


# A ले आफैंलाई पर्खँदा error
def test_self_dependency_fails():
    definition = {
        "tasks": [
            {"name": "A", "depends_on": ["A"]},
        ]
    }
    try:
        get_execution_order(definition)
        assert False, "Expected WorkflowValidationError for self-dependency"
    except WorkflowValidationError as e:
        assert "cannot depend on itself" in str(e).lower()


# Z (स्वतन्त्र) + X ↔ Y। Message मा X र Y छन्, Z छैन
def test_cycle_message_has_stuck_names():
    definition = {
        "tasks": [
            {"name": "Z", "depends_on": []},
            {"name": "X", "depends_on": ["Y"]},
            {"name": "Y", "depends_on": ["X"]},
        ]
    }
    try:
        get_execution_order(definition)
        assert False, "Expected WorkflowValidationError for cycle"
    except WorkflowValidationError as e:
        assert "cycle" in str(e).lower()
        assert "X" in str(e)
        assert "Y" in str(e)
        assert "Z" not in str(e)

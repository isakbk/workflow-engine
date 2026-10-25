from engine.validators import validate_definition

from engine.validators import WorkflowValidationError

import pytest


def test_valid_definition_passes():

    definition = []

    with pytest.raises(
        WorkflowValidationError, match="Definition must be a dictionary"
    ):

        validate_definition(definition)


def test_missing_tasks_key_fails():

    definition = {}

    with pytest.raises(
        WorkflowValidationError, match="Definition must have a 'tasks' key"
    ):

        validate_definition(definition)


def test_tasks_not_a_list_fails():

    definition = {"tasks": {}}

    with pytest.raises(WorkflowValidationError, match="Tasks must be a list"):

        validate_definition(definition)


def test_empty_tasks_fails():

    definition = {"tasks": []}

    with pytest.raises(WorkflowValidationError, match="Tasks must not be empty"):

        validate_definition(definition)


# additional


def test_task_missing_name_fails():

    definition = {"tasks": [{"name": "open"}, {"fn": "close"}]}

    with pytest.raises(
        WorkflowValidationError, match="Tasks must have 'name' and 'fn' keys"
    ):

        validate_definition(definition)


def test_task_empty_name_fails():

    definition = {"tasks": [{"name": "", "fn": "close"}]}

    with pytest.raises(WorkflowValidationError, match="Tasks name must not be empty"):

        validate_definition(definition)


def test_task_missing_fn_fails():

    definition = {"tasks": [{"name": "open"}]}

    with pytest.raises(
        WorkflowValidationError, match="Tasks must have 'name' and 'fn' keys"
    ):

        validate_definition(definition)


def test_task_not_a_dict_fails():

    definition = ["open"]

    with pytest.raises(
        WorkflowValidationError, match="Definition must be a dictionary"
    ):

        validate_definition(definition)


# addition 2
def test_duplicate_task_name_fails():
    definition = {
        "tasks": [{"name": "open", "fn": "open"}, {"name": "open", "fn": "close"}]
    }
    with pytest.raises(WorkflowValidationError, match="Duplicate task name"):
        validate_definition(definition)


def test_missing_dependency_fails():
    definition = {"tasks": [{"name": "open", "fn": "open", "depends_on": ["close"]}]}
    with pytest.raises(WorkflowValidationError, match="Missing dependency"):
        validate_definition(definition)


def test_depends_on_not_a_list_fails():
    definition = {"tasks": [{"name": "open", "fn": "open", "depends_on": "close"}]}
    with pytest.raises(WorkflowValidationError, match="Depends on must be a list"):
        validate_definition(definition)


def test_valid_dependencies_pass():
    definition = {
        "tasks": [
            {"name": "open", "fn": "open"},
            {"name": "close", "fn": "close", "depends_on": ["open"]},
        ]
    }
    validate_definition(definition)  # Should not raise



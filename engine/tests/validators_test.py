from engine.validators import validate_definition
from engine.validators import WorkflowValidationError
import pytest 

def test_valid_definition_passes():
    definition=[]
    with pytest.raises(WorkflowValidationError,match="Definition must be a dictionary"):
        validate_definition(definition)

def test_missing_tasks_key_fails():
    definition={}
    with pytest.raises(WorkflowValidationError,match="Definition must have a 'tasks' key"):
        validate_definition(definition)

def test_tasks_not_a_list_fails():
    definition={"tasks":{}}
    with pytest.raises(WorkflowValidationError,match="Tasks must be a list"):
        validate_definition(definition)

def test_empty_tasks_fails():
    definition={"tasks":[]}
    with pytest.raises(WorkflowValidationError,match="Tasks must not be empty"):
        validate_definition(definition)
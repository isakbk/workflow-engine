class WorkflowValidationError(ValueError):
    pass


def validate_definition(definition):
    if not isinstance(definition, dict):
        raise WorkflowValidationError("Definition must be a dictionary")
   
    if "tasks" not in definition:
        raise WorkflowValidationError("Definition must have a 'tasks' key")
   
    if not isinstance(definition["tasks"], list):
        raise WorkflowValidationError("Tasks must be a list")
   
    if len(definition["tasks"]) == 0:
        raise WorkflowValidationError("Tasks must not be empty")
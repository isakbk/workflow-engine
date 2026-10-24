class WorkflowValidationError(ValueError):
    pass


def key_checker(definition):
    required_keys = ["name", "fn"]

    for number, task in enumerate(definition["tasks"], start=1):
        for key in required_keys:
            if key not in task:
                print(f"Task {number}: Missing key '{key}'")
                return False

    return True


def value_empty_checker(definition):
    for number, task in enumerate(definition["tasks"], start=1):
        if not task["name"].strip():
            return False

    return True


def duplicate_task_name(definition):
    task_names = [task["name"] for task in definition["tasks"]]
    if len(task_names) != len(set(task_names)):
        return False
    return True


def check_dependencies(definition):
    task_names = [task["name"] for task in definition["tasks"]]
    for task in definition["tasks"]:
        if "depends_on" in task:
            for dependency in task["depends_on"]:
                if dependency not in task_names:
                    return False
    return True


def check_depends_on_type(definition):
    for task in definition["tasks"]:
        if "depends_on" in task:
            if not isinstance(task["depends_on"], list):
                return False
    return True


# main


def validate_definition(definition):
    if not isinstance(definition, dict):
        raise WorkflowValidationError("Definition must be a dictionary")

    if "tasks" not in definition:
        raise WorkflowValidationError("Definition must have a 'tasks' key")

    if not isinstance(definition["tasks"], list):
        raise WorkflowValidationError("Tasks must be a list")

    if len(definition["tasks"]) == 0:
        raise WorkflowValidationError("Tasks must not be empty")

    if not key_checker(definition):
        raise WorkflowValidationError("Tasks must have 'name' and 'fn' keys")

    if not value_empty_checker(definition):
        raise WorkflowValidationError("Tasks name must not be empty")

    if not duplicate_task_name(definition):
        raise WorkflowValidationError("Duplicate task name")

    if not check_depends_on_type(definition):
        raise WorkflowValidationError("Depends on must be a list")

    if not check_dependencies(definition):
        raise WorkflowValidationError("Missing dependency")

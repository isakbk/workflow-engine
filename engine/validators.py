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





def get_execution_order(definition):
    # Step 1: Validate definition
    if not isinstance(definition, dict):
        raise WorkflowValidationError(
            "Definition must be a dictionary"
        )

    tasks = definition.get("tasks")

    if not isinstance(tasks, list) or not tasks:
        raise WorkflowValidationError(
            "Definition must contain a non-empty tasks list"
        )

    # Step 2: Validate task names and initialize dictionaries
    in_degree = {}
    dependents = {}

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise WorkflowValidationError(
                f"Task at position {index + 1} must be a dictionary"
            )

        name = task.get("name")

        if not isinstance(name, str) or not name.strip():
            raise WorkflowValidationError(
                f"Task at position {index + 1} has an invalid name"
            )

        if name in in_degree:
            raise WorkflowValidationError(
                f"Duplicate task name: {name}"
            )

        in_degree[name] = 0
        dependents[name] = []

    # Step 3: Validate dependencies
    for task in tasks:
        name = task["name"]
        dependencies = task.get("depends_on", [])

        if not isinstance(dependencies, list):
            raise WorkflowValidationError(
                f"Task '{name}' depends_on must be a list"
            )

        for dependency in dependencies:

            # A -> A: self-dependency
            if dependency == name:
                raise WorkflowValidationError(
                    f"Task '{name}' cannot depend on itself"
                )

            # Dependency must refer to an existing task
            if dependency not in in_degree:
                raise WorkflowValidationError(
                    f"Task '{name}' depends on unknown task "
                    f"'{dependency}'"
                )

            # Build graph
            in_degree[name] += 1
            dependents[dependency].append(name)

    # Step 4: Find tasks with zero in-degree
    ready = [
        name
        for name, degree in in_degree.items()
        if degree == 0
    ]

    # Step 5: Kahn's algorithm
    order = []

    while ready:
        current = ready.pop(0)
        order.append(current)

        for next_task in dependents[current]:
            in_degree[next_task] -= 1

            if in_degree[next_task] == 0:
                ready.append(next_task)

    # Step 6: Detect cycles
    if len(order) != len(tasks):
        stuck_tasks = [
            name
            for name, degree in in_degree.items()
            if degree > 0
        ]

        raise WorkflowValidationError(
            f"Cycle detected. Stuck tasks: {stuck_tasks}"
        )

    return order






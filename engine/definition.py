
def validate_definition(definition):
    errors = []

    # 1. Definition must be a dictionary
    if not isinstance(definition, dict):
        return ["definition must be a dictionary"]

    # 2. Tasks must exist and be a list
    if "tasks" not in definition:
        return ["tasks key is required"]

    tasks = definition["tasks"]

    if not isinstance(tasks, list):
        return ["tasks must be a list"]

    allowed_keys = {
        "name",
        "fn",
        "depends_on",
        "max_attempts",
        "timeout_seconds"
    }

    valid_names = []
    valid_dependencies = []
    reported_duplicates = set()

    # 3. Validate each task
    for task in tasks:

        if not isinstance(task, dict):
            errors.append("task must be a dictionary")
            continue

        # Unknown keys
        for key in task:
            if key not in allowed_keys:
                errors.append(f"unknown task key: {key}")

        # Validate name
        name = task.get("name")

        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            errors.append("name must be a non-empty string up to 100 characters")
        else:
            if name in valid_names and name not in reported_duplicates:
                errors.append(f"duplicate task name: {name}")
                reported_duplicates.add(name)

            valid_names.append(name)

        # Validate fn
        fn = task.get("fn")

        if not isinstance(fn, str) or not fn.strip() or len(fn) > 100:
            errors.append("fn must be a non-empty string up to 100 characters")

        # Validate depends_on
        if "depends_on" in task:
            depends = task["depends_on"]

            if not isinstance(depends, list) or not all(
                isinstance(dep, str) for dep in depends
            ):
                errors.append("depends_on must be a list of strings")
            else:
                valid_dependencies.append(depends)

        # Validate max_attempts
        if "max_attempts" in task:
            value = task["max_attempts"]

            if type(value) is not int or value < 1:
                errors.append("max_attempts must be a positive integer")

        # Validate timeout_seconds
        if "timeout_seconds" in task:
            value = task["timeout_seconds"]

            if type(value) is not int or value < 1:
                errors.append("timeout_seconds must be a positive integer")

    # 4. Validate dependencies after collecting all task names
    for dependencies in valid_dependencies:
        for dependency in dependencies:
            if dependency not in valid_names:
                errors.append(f"unknown dependency: {dependency}")

    return errors

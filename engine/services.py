
from engine.models import Run, TaskRun
from engine.definition import validate_definition, build_graph,validate_executors
from engine.graph import find_cycle
from django.db import transaction


class RunNotAllowed(ValueError):
    pass


def create_run(workflow, trigger="MANUAL"):

    # 1. Check workflow status
    if not workflow.is_active:
        raise RunNotAllowed("Workflow is inactive.")

    # 2. Validate tasks structure
    definition = workflow.definition

    if not isinstance(definition, dict):
        raise RunNotAllowed("Workflow has no tasks.")

    tasks = definition.get("tasks")

    if not isinstance(tasks, list) or not tasks:
        raise RunNotAllowed("Workflow has no tasks.")

    # 3. Validate workflow definition
    errors = validate_definition(definition)
    execution_error=validate_executors(definition)
    errors.extend(execution_error)

    if errors:
        raise RunNotAllowed("Workflow definition is invalid.")

    # 4. Detect cycle
    cycle = find_cycle(build_graph(definition))

    if cycle:
        raise RunNotAllowed("Workflow definition is invalid.")

    # 5. Create Run and TaskRuns atomically
    with transaction.atomic():

        run = Run.objects.create(
            workflow=workflow,
            trigger=trigger
        )

        task_runs = []

        for task in tasks:
            task_runs.append(
                TaskRun(
                    run=run,
                    name=task["name"],
                    fn=task["fn"],
                    depends_on=task.get("depends_on", []).copy(),
                    max_attempts=task.get("max_attempts", 3),
                    timeout_seconds=task.get("timeout_seconds", 60),
                    idempotency_key=f"run-{run.id}:{task['name']}"
                )
            )

        TaskRun.objects.bulk_create(task_runs)

    return run


from django.utils import timezone

from engine.models import TaskRun


class InvalidTransition(ValueError):
    pass


TASK_TRANSITIONS = {
    "PENDING": ["QUEUED", "SKIPPED", "CANCELLED"],
    "QUEUED": ["RUNNING", "CANCELLED"],
    "RUNNING": ["SUCCESS", "FAILED", "CANCELLED"],
    "FAILED": ["RETRYING", "DEAD"],
    "RETRYING": ["QUEUED", "CANCELLED"],
    "SUCCESS": [],
    "DEAD": [],
    "SKIPPED": [],
    "CANCELLED": [],
}


def can_transition(current_status, new):
    return new in TASK_TRANSITIONS.get(current_status, [])


def set_status(task_run, new_status, now=timezone.now):
    if not can_transition(task_run.status, new_status):
        raise InvalidTransition(
            f"Cannot go from {task_run.status} to {new_status}."
        )

    task_run.status = new_status

    if new_status == "RUNNING" and task_run.started_at is None:
        task_run.started_at = now()

    if (
        new_status in TaskRun.TERMINAL
        and task_run.finished_at is None
    ):
        task_run.finished_at = now()

    task_run.save()

    return task_run


def refresh_run_status(run, now=timezone.now):

    statuses = list(
        run.task_runs.values_list("status", flat=True)
    )

    # 1. No TaskRun
    if not statuses:
        return run

    # 2. All SUCCESS
    if all(status == "SUCCESS" for status in statuses):
        new_status = "SUCCESS"

    # 3. All TERMINAL
    elif all(status in TaskRun.TERMINAL for status in statuses):

        if any(status in ["DEAD", "SKIPPED"] for status in statuses):
            new_status = "FAILED"
        else:
            new_status = "CANCELLED"

    # 4. Not all TERMINAL
    elif all(status == "PENDING" for status in statuses):
        new_status = "PENDING"

    else:
        new_status = "RUNNING"

    run.status = new_status

    # Set started_at
    if new_status == "RUNNING" and run.started_at is None:
        run.started_at = now()

    # Set finished_at
    if (
        new_status in ["SUCCESS", "FAILED", "CANCELLED"]
        and run.finished_at is None
    ):
        run.finished_at = now()

    run.save()

    return run

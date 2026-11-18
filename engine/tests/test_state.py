from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from django.utils import timezone

from engine.models import Run, TaskRun, Workflow
from engine.state import (
    InvalidTransition,
    can_transition,
    refresh_run_status,
    set_status,
)

T1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt_timezone.utc)
T2 = T1 + timedelta(minutes=1)
T3 = T1 + timedelta(minutes=2)
T4 = T1 + timedelta(minutes=3)
T5 = T1 + timedelta(minutes=4)

ALL_STATUSES = [
    "PENDING", "QUEUED", "RUNNING", "SUCCESS", "FAILED",
    "RETRYING", "DEAD", "SKIPPED", "CANCELLED",
]

ALLOWED = {
    "PENDING": {"QUEUED", "SKIPPED", "CANCELLED"},
    "QUEUED": {"RUNNING", "CANCELLED"},
    "RUNNING": {"SUCCESS", "FAILED", "CANCELLED"},
    "FAILED": {"RETRYING", "DEAD"},
    "RETRYING": {"QUEUED", "CANCELLED"},
}


def reload(obj):
    return type(obj).objects.get(id=obj.id)


def make_task_run(status="PENDING"):
    workflow = Workflow.objects.create(name="wf")
    run = Run.objects.create(workflow=workflow)
    return TaskRun.objects.create(
        run=run, name="a", fn="echo", status=status,
        idempotency_key=f"t12-{run.id}:a",
    )


def make_run(statuses, workflow=None):
    if workflow is None:
        workflow = Workflow.objects.create(name="wf")
    run = Run.objects.create(workflow=workflow)
    for index, status in enumerate(statuses):
        TaskRun.objects.create(
            run=run, name=f"t{index}", fn="echo", status=status,
            idempotency_key=f"t12-{run.id}:t{index}",
        )
    return run


# ---------- can_transition ----------

def test_can_transition_matches_the_table():
    for old in ALL_STATUSES:
        for new in ALL_STATUSES:
            expected = new in ALLOWED.get(old, set())
            assert can_transition(old, new) is expected, f"{old} -> {new}"


def test_can_transition_rejects_unknown_status():
    assert can_transition("BOGUS", "RUNNING") is False
    assert can_transition("PENDING", "BOGUS") is False


# ---------- set_status ----------

@pytest.mark.django_db
def test_set_status_changes_status_and_saves():
    task_run = make_task_run("PENDING")
    result = set_status(task_run, "QUEUED", now=lambda: T1)
    assert result.status == "QUEUED"
    assert reload(task_run).status == "QUEUED"


@pytest.mark.django_db
def test_set_status_rejects_invalid_transition():
    task_run = make_task_run("PENDING")
    with pytest.raises(InvalidTransition) as error:
        set_status(task_run, "RUNNING", now=lambda: T1)
    assert str(error.value) == "Cannot go from PENDING to RUNNING."
    assert task_run.status == "PENDING"
    saved = reload(task_run)
    assert saved.status == "PENDING"
    assert saved.started_at is None


@pytest.mark.django_db
def test_set_status_rejects_unknown_status():
    task_run = make_task_run("PENDING")
    with pytest.raises(InvalidTransition) as error:
        set_status(task_run, "BOGUS", now=lambda: T1)
    assert str(error.value) == "Cannot go from PENDING to BOGUS."
    assert reload(task_run).status == "PENDING"


@pytest.mark.django_db
def test_running_sets_started_at():
    task_run = make_task_run("QUEUED")
    set_status(task_run, "RUNNING", now=lambda: T1)
    saved = reload(task_run)
    assert saved.status == "RUNNING"
    assert saved.started_at == T1
    assert saved.finished_at is None


@pytest.mark.django_db
def test_second_running_keeps_first_started_at():
    task_run = make_task_run("QUEUED")
    set_status(task_run, "RUNNING", now=lambda: T1)
    set_status(task_run, "FAILED", now=lambda: T2)
    set_status(task_run, "RETRYING", now=lambda: T3)
    set_status(task_run, "QUEUED", now=lambda: T4)
    set_status(task_run, "RUNNING", now=lambda: T5)
    saved = reload(task_run)
    assert saved.status == "RUNNING"
    assert saved.started_at == T1
    assert saved.finished_at is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "start,end",
    [
        ("RUNNING", "SUCCESS"),
        ("FAILED", "DEAD"),
        ("PENDING", "SKIPPED"),
        ("PENDING", "CANCELLED"),
    ],
)
def test_terminal_status_sets_finished_at(start, end):
    task_run = make_task_run(start)
    set_status(task_run, end, now=lambda: T2)
    saved = reload(task_run)
    assert saved.status == end
    assert saved.finished_at == T2


@pytest.mark.django_db
def test_failed_and_retrying_do_not_set_finished_at():
    task_run = make_task_run("RUNNING")
    set_status(task_run, "FAILED", now=lambda: T1)
    assert reload(task_run).finished_at is None
    set_status(task_run, "RETRYING", now=lambda: T2)
    assert reload(task_run).finished_at is None


@pytest.mark.django_db
def test_set_status_uses_real_clock_by_default():
    task_run = make_task_run("QUEUED")
    set_status(task_run, "RUNNING")
    saved = reload(task_run)
    assert saved.started_at is not None
    assert abs((saved.started_at - timezone.now()).total_seconds()) < 60


# ---------- refresh_run_status ----------

@pytest.mark.django_db
def test_refresh_all_success_gives_success():
    run = make_run(["SUCCESS", "SUCCESS"])
    result = refresh_run_status(run, now=lambda: T1)
    assert result.id == run.id
    saved = reload(run)
    assert saved.status == "SUCCESS"
    assert saved.finished_at == T1


@pytest.mark.django_db
def test_refresh_all_pending_stays_pending():
    run = make_run(["PENDING", "PENDING"])
    refresh_run_status(run, now=lambda: T1)
    saved = reload(run)
    assert saved.status == "PENDING"
    assert saved.started_at is None
    assert saved.finished_at is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "statuses",
    [
        ["PENDING", "QUEUED"],
        ["PENDING", "RUNNING"],
        ["SUCCESS", "PENDING"],
        ["SUCCESS", "RETRYING"],
        ["SUCCESS", "FAILED"],
        ["DEAD", "RUNNING"],
    ],
)
def test_refresh_unfinished_run_is_running(statuses):
    run = make_run(statuses)
    refresh_run_status(run, now=lambda: T1)
    saved = reload(run)
    assert saved.status == "RUNNING"
    assert saved.started_at == T1
    assert saved.finished_at is None


@pytest.mark.django_db
def test_refresh_running_keeps_first_started_at():
    run = make_run(["QUEUED", "PENDING"])
    refresh_run_status(run, now=lambda: T1)
    TaskRun.objects.filter(run=run, name="t0").update(status="RUNNING")
    refresh_run_status(run, now=lambda: T2)
    saved = reload(run)
    assert saved.status == "RUNNING"
    assert saved.started_at == T1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "statuses",
    [
        ["SUCCESS", "DEAD"],
        ["DEAD", "SKIPPED", "SUCCESS"],
        ["SUCCESS", "SKIPPED"],
    ],
)
def test_refresh_dead_or_skipped_gives_failed(statuses):
    run = make_run(statuses)
    refresh_run_status(run, now=lambda: T1)
    saved = reload(run)
    assert saved.status == "FAILED"
    assert saved.finished_at == T1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "statuses",
    [["CANCELLED", "CANCELLED"], ["SUCCESS", "CANCELLED"]],
)
def test_refresh_cancelled_gives_cancelled(statuses):
    run = make_run(statuses)
    refresh_run_status(run, now=lambda: T1)
    saved = reload(run)
    assert saved.status == "CANCELLED"
    assert saved.finished_at == T1


@pytest.mark.django_db
def test_refresh_dead_beats_cancelled():
    run = make_run(["DEAD", "CANCELLED"])
    refresh_run_status(run, now=lambda: T1)
    assert reload(run).status == "FAILED"


@pytest.mark.django_db
def test_refresh_run_without_task_runs_is_unchanged():
    run = make_run([])
    refresh_run_status(run, now=lambda: T1)
    saved = reload(run)
    assert saved.status == "PENDING"
    assert saved.started_at is None
    assert saved.finished_at is None


@pytest.mark.django_db
def test_refresh_does_not_overwrite_finished_at():
    run = make_run(["SUCCESS"])
    refresh_run_status(run, now=lambda: T1)
    refresh_run_status(run, now=lambda: T2)
    saved = reload(run)
    assert saved.status == "SUCCESS"
    assert saved.finished_at == T1


@pytest.mark.django_db
def test_refresh_ignores_task_runs_of_other_runs():
    workflow = Workflow.objects.create(name="shared")
    run_a = make_run(["SUCCESS"], workflow)
    make_run(["DEAD"], workflow)
    refresh_run_status(run_a, now=lambda: T1)
    assert reload(run_a).status == "SUCCESS"
import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.utils import timezone
from engine.models import Run, TaskRun, Workflow


@pytest.fixture
def run():
    workflow = Workflow.objects.create(name="daily_sales")
    return Run.objects.create(workflow=workflow)


def make_task_run(run, name="extract", key=None, **extra):
    return TaskRun.objects.create(
        run=run,
        name=name,
        fn="echo",
        idempotency_key=key or f"key-{run.id}-{name}",
        **extra,
    )


@pytest.mark.django_db
def test_task_run_defaults(run):
    created = make_task_run(run)
    saved = TaskRun.objects.get(id=created.id)
    assert saved.depends_on == []
    assert saved.status == "PENDING"
    assert saved.attempt == 0
    assert saved.max_attempts == 3
    assert saved.timeout_seconds == 60
    assert saved.next_retry_at is None
    assert saved.last_heartbeat is None
    assert saved.worker_id == ""
    assert saved.output is None
    assert saved.error == ""
    assert saved.started_at is None
    assert saved.finished_at is None


@pytest.mark.django_db
def test_status_accepts_the_nine_specified_values(run):
    values = ["PENDING", "QUEUED", "RUNNING", "SUCCESS", "FAILED",
              "RETRYING", "DEAD", "SKIPPED", "CANCELLED"]
    for value in values:
        TaskRun(run=run, name="t", fn="echo", idempotency_key="k", status=value).full_clean()


@pytest.mark.django_db
def test_status_rejects_unknown_value(run):
    with pytest.raises(ValidationError):
        TaskRun(run=run, name="t", fn="echo", idempotency_key="k", status="PAUSED").full_clean()


def test_terminal_statuses_are_exactly_four():
    assert set(TaskRun.TERMINAL) == {"SUCCESS", "DEAD", "SKIPPED", "CANCELLED"}


@pytest.mark.django_db
def test_depends_on_and_output_store_json(run):
    created = make_task_run(run, depends_on=["extract", "clean"], output={"rows": 5, "ok": True})
    saved = TaskRun.objects.get(id=created.id)
    assert saved.depends_on == ["extract", "clean"]
    assert saved.output == {"rows": 5, "ok": True}


@pytest.mark.django_db
def test_optional_fields_can_be_left_blank(run):
    TaskRun(run=run, name="t", fn="echo", idempotency_key="k").full_clean()


@pytest.mark.django_db
def test_str_shows_run_id_and_task_name(run):
    task_run = make_task_run(run, name="extract")
    assert str(task_run) == f"Run #{run.id}: extract"


@pytest.mark.django_db
def test_run_has_task_runs_related_name(run):
    make_task_run(run, name="extract")
    make_task_run(run, name="load")
    assert run.task_runs.count() == 2


@pytest.mark.django_db
def test_deleting_run_deletes_its_task_runs(run):
    make_task_run(run)
    run.delete()
    assert TaskRun.objects.count() == 0


@pytest.mark.django_db
def test_text_and_number_limits(run):
    TaskRun(run=run, name="n" * 100, fn="f" * 100, idempotency_key="k" * 200).full_clean()
    bad_values = [
        ("name", "n" * 101),
        ("fn", "f" * 101),
        ("idempotency_key", "k" * 201),
        ("attempt", -1),
        ("max_attempts", -1),
        ("timeout_seconds", -1),
    ]
    for field, value in bad_values:
        data = {"name": "t", "fn": "echo", "idempotency_key": "k"}
        data[field] = value
        with pytest.raises(ValidationError):
            TaskRun(run=run, **data).full_clean()


@pytest.mark.django_db
def test_timestamps_are_stored(run):
    moment = timezone.now()
    created = make_task_run(
        run, next_retry_at=moment, last_heartbeat=moment, started_at=moment, finished_at=moment
    )
    saved = TaskRun.objects.get(id=created.id)
    assert saved.next_retry_at == moment
    assert saved.last_heartbeat == moment
    assert saved.started_at == moment
    assert saved.finished_at == moment


def test_task_run_has_exactly_the_specified_fields():
    names = {field.name for field in TaskRun._meta.concrete_fields}
    assert names == {
        "id", "run", "name", "fn", "depends_on", "status", "attempt", "max_attempts",
        "timeout_seconds", "next_retry_at", "last_heartbeat", "worker_id",
        "idempotency_key", "output", "error", "started_at", "finished_at",
    }


def test_task_run_is_registered_in_admin():
    assert admin.site.is_registered(TaskRun)


def test_indexes_are_defined():
    indexes = {index.name: tuple(index.fields) for index in TaskRun._meta.indexes}
    assert indexes == {
        "task_status_retry_idx": ("status", "next_retry_at"),
        "task_status_heartbeat_idx": ("status", "last_heartbeat"),
        "task_run_status_idx": ("run", "status"),
    }


@pytest.mark.django_db
def test_no_model_changes_without_migration():
    try:
        call_command("makemigrations", "--check", "--dry-run")
    except SystemExit:
        pytest.fail("Model changed but no migration exists. Run: python manage.py makemigrations engine")


@pytest.mark.django_db
def test_same_task_name_is_allowed_in_different_runs(run):
    other = Run.objects.create(workflow=run.workflow)
    make_task_run(run, name="extract")
    make_task_run(other, name="extract")
    assert TaskRun.objects.filter(name="extract").count() == 2


@pytest.mark.django_db
def test_task_name_must_be_unique_within_a_run(run):
    make_task_run(run, name="extract", key="k1")
    with pytest.raises(IntegrityError):
        make_task_run(run, name="extract", key="k2")


@pytest.mark.django_db
def test_idempotency_key_must_be_unique(run):
    other = Run.objects.create(workflow=run.workflow)
    make_task_run(run, name="extract", key="same-key")
    with pytest.raises(IntegrityError):
        make_task_run(other, name="load", key="same-key")
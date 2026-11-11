import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.utils import timezone
from engine.models import Attempt, Run, TaskRun, Workflow


@pytest.fixture
def task_run():
    workflow = Workflow.objects.create(name="daily_sales")
    run = Run.objects.create(workflow=workflow)
    return TaskRun.objects.create(run=run, name="extract", fn="echo", idempotency_key="k1")


def make_attempt(task_run, number=1, **extra):
    data = {"status": "SUCCESS", "worker_id": "worker-1", "started_at": timezone.now()}
    data.update(extra)
    return Attempt.objects.create(task_run=task_run, number=number, **data)


@pytest.mark.django_db
def test_attempt_defaults(task_run):
    saved = Attempt.objects.get(id=make_attempt(task_run).id)
    assert saved.number == 1
    assert saved.finished_at is None
    assert saved.error == ""


@pytest.mark.django_db
def test_attempt_stores_values(task_run):
    moment = timezone.now()
    created = make_attempt(
        task_run, number=2, status="FAILED", worker_id="worker-9",
        started_at=moment, finished_at=moment, error="boom",
    )
    saved = Attempt.objects.get(id=created.id)
    assert saved.status == "FAILED"
    assert saved.worker_id == "worker-9"
    assert saved.started_at == moment
    assert saved.finished_at == moment
    assert saved.error == "boom"


@pytest.mark.django_db
def test_status_only_allows_success_and_failed(task_run):
    for value in ["SUCCESS", "FAILED"]:
        Attempt(
            task_run=task_run, number=1, status=value,
            worker_id="w1", started_at=timezone.now(),
        ).full_clean()
    with pytest.raises(ValidationError):
        Attempt(
            task_run=task_run, number=1, status="RUNNING",
            worker_id="w1", started_at=timezone.now(),
        ).full_clean()


@pytest.mark.django_db
def test_started_at_and_worker_id_are_required(task_run):
    with pytest.raises(ValidationError):
        Attempt(task_run=task_run, number=1, status="SUCCESS", worker_id="w1").full_clean()
    with pytest.raises(ValidationError):
        Attempt(
            task_run=task_run, number=1, status="SUCCESS", started_at=timezone.now()
        ).full_clean()


@pytest.mark.django_db
def test_negative_number_is_rejected(task_run):
    with pytest.raises(ValidationError):
        Attempt(
            task_run=task_run, number=-1, status="SUCCESS",
            worker_id="w1", started_at=timezone.now(),
        ).full_clean()


@pytest.mark.django_db
def test_str_shows_task_name_and_attempt_number(task_run):
    attempt = make_attempt(task_run, number=2)
    assert str(attempt) == "extract - Attempt 2"


@pytest.mark.django_db
def test_task_run_has_attempts_related_name(task_run):
    make_attempt(task_run, number=1)
    make_attempt(task_run, number=2)
    assert task_run.attempts.count() == 2


@pytest.mark.django_db
def test_attempts_are_ordered_by_number(task_run):
    for number in [3, 1, 2]:
        make_attempt(task_run, number=number)
    assert [a.number for a in task_run.attempts.all()] == [1, 2, 3]


@pytest.mark.django_db
def test_deleting_task_run_deletes_its_attempts(task_run):
    make_attempt(task_run)
    task_run.delete()
    assert Attempt.objects.count() == 0


def test_attempt_has_exactly_the_specified_fields():
    names = {field.name for field in Attempt._meta.concrete_fields}
    assert names == {"id", "task_run", "number", "status", "worker_id",
                     "started_at", "finished_at", "error"}


def test_attempt_is_registered_in_admin():
    assert admin.site.is_registered(Attempt)


@pytest.mark.django_db
def test_no_model_changes_without_migration():
    try:
        call_command("makemigrations", "--check", "--dry-run")
    except SystemExit:
        pytest.fail("Model changed but no migration exists. Run: python manage.py makemigrations engine")


@pytest.mark.django_db
def test_same_attempt_number_is_allowed_on_different_task_runs(task_run):
    other = TaskRun.objects.create(run=task_run.run, name="load", fn="echo", idempotency_key="k2")
    make_attempt(task_run, number=1)
    make_attempt(other, number=1)
    assert Attempt.objects.filter(number=1).count() == 2


@pytest.mark.django_db
def test_attempt_number_must_be_unique_per_task_run(task_run):
    make_attempt(task_run, number=1)
    with pytest.raises(IntegrityError):
        make_attempt(task_run, number=1)
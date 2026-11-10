import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone
from engine.models import Run, Workflow


@pytest.fixture
def workflow():
    return Workflow.objects.create(name="daily_sales")


@pytest.mark.django_db
def test_run_defaults(workflow):
    created = Run.objects.create(workflow=workflow)
    saved = Run.objects.get(id=created.id)
    assert saved.status == "PENDING"
    assert saved.trigger == "MANUAL"
    assert saved.created_at is not None
    assert saved.started_at is None
    assert saved.finished_at is None


@pytest.mark.django_db
def test_status_accepts_the_five_specified_values(workflow):
    for value in ["PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"]:
        Run(workflow=workflow, status=value).full_clean()


@pytest.mark.django_db
def test_status_rejects_unknown_value(workflow):
    with pytest.raises(ValidationError):
        Run(workflow=workflow, status="DONE").full_clean()


@pytest.mark.django_db
def test_trigger_accepts_manual_and_cron(workflow):
    for value in ["MANUAL", "CRON"]:
        Run(workflow=workflow, trigger=value).full_clean()


@pytest.mark.django_db
def test_trigger_rejects_unknown_value(workflow):
    with pytest.raises(ValidationError):
        Run(workflow=workflow, trigger="WEBHOOK").full_clean()


@pytest.mark.django_db
def test_str_shows_run_id_and_workflow_name(workflow):
    run = Run.objects.create(workflow=workflow)
    assert str(run) == f"Run #{run.id} of daily_sales"


@pytest.mark.django_db
def test_workflow_has_runs_related_name(workflow):
    Run.objects.create(workflow=workflow)
    Run.objects.create(workflow=workflow, trigger="CRON")
    assert workflow.runs.count() == 2


@pytest.mark.django_db
def test_deleting_workflow_deletes_its_runs(workflow):
    Run.objects.create(workflow=workflow)
    workflow.delete()
    assert Run.objects.count() == 0


@pytest.mark.django_db
def test_started_and_finished_timestamps_are_stored(workflow):
    moment = timezone.now()
    created = Run.objects.create(workflow=workflow, started_at=moment, finished_at=moment)
    saved = Run.objects.get(id=created.id)
    assert saved.started_at == moment
    assert saved.finished_at == moment


def test_run_has_exactly_the_specified_fields():
    names = {field.name for field in Run._meta.concrete_fields}
    assert names == {"id", "workflow", "status", "trigger", "created_at", "started_at", "finished_at"}


def test_run_is_registered_in_admin():
    assert admin.site.is_registered(Run)


@pytest.mark.django_db
def test_no_model_changes_without_migration():
    try:
        call_command("makemigrations", "--check", "--dry-run")
    except SystemExit:
        pytest.fail("Model changed but no migration exists. Run: python manage.py makemigrations engine")
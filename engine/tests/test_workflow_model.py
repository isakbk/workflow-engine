import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.db.migrations.loader import MigrationLoader
from engine.models import Workflow

VALID_DEFINITION = {"tasks": []}


@pytest.mark.django_db
def test_workflow_defaults():
    created = Workflow.objects.create(name="daily_sales")
    saved = Workflow.objects.get(id=created.id)
    assert saved.name == "daily_sales"
    assert saved.definition == {}
    assert saved.cron == ""
    assert saved.is_active is True
    assert saved.version == 1
    assert saved.created_at is not None


@pytest.mark.django_db
def test_workflow_stores_definition_json():
    definition = {"tasks": [{"name": "a", "fn": "echo", "depends_on": []}]}
    created = Workflow.objects.create(name="with_tasks", definition=definition)
    saved = Workflow.objects.get(id=created.id)
    assert saved.definition == definition


@pytest.mark.django_db
def test_workflow_stores_cron_version_and_inactive_flag():
    created = Workflow.objects.create(
        name="nightly", cron="0 2 * * *", version=3, is_active=False
    )
    saved = Workflow.objects.get(id=created.id)
    assert saved.cron == "0 2 * * *"
    assert saved.version == 3
    assert saved.is_active is False


@pytest.mark.django_db
def test_name_cannot_be_blank():
    with pytest.raises(ValidationError):
        Workflow(name="", definition=VALID_DEFINITION).full_clean()


@pytest.mark.django_db
def test_name_max_length_is_100():
    Workflow(name="x" * 100, definition=VALID_DEFINITION).full_clean()
    with pytest.raises(ValidationError):
        Workflow(name="x" * 101, definition=VALID_DEFINITION).full_clean()


@pytest.mark.django_db
def test_cron_can_be_blank():
    Workflow(name="manual_only", definition=VALID_DEFINITION, cron="").full_clean()


@pytest.mark.django_db
def test_cron_max_length_is_50():
    Workflow(name="c50", definition=VALID_DEFINITION, cron="c" * 50).full_clean()
    with pytest.raises(ValidationError):
        Workflow(name="c51", definition=VALID_DEFINITION, cron="c" * 51).full_clean()


@pytest.mark.django_db
def test_str_returns_name():
    assert str(Workflow.objects.create(name="report")) == "report"


def test_workflow_has_exactly_the_specified_fields():
    names = {field.name for field in Workflow._meta.concrete_fields}
    assert names == {"id", "name", "definition", "cron", "is_active", "version", "created_at"}


def test_workflow_is_registered_in_admin():
    assert admin.site.is_registered(Workflow)


def test_engine_has_a_migration_file():
    loader = MigrationLoader(None)
    assert any(app == "engine" for app, _name in loader.disk_migrations)


@pytest.mark.django_db
def test_no_model_changes_without_migration():
    try:
        call_command("makemigrations", "--check", "--dry-run")
    except SystemExit:
        pytest.fail("Model changed but no migration exists. Run: python manage.py makemigrations engine")


@pytest.mark.django_db
def test_name_must_be_unique():
    Workflow.objects.create(name="dup")
    with pytest.raises(IntegrityError):
        Workflow.objects.create(name="dup")
import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from engine.models import IdempotencyRecord


@pytest.mark.django_db
def test_record_defaults():
    created = IdempotencyRecord.objects.create(key="run1:extract")
    saved = IdempotencyRecord.objects.get(id=created.id)
    assert saved.key == "run1:extract"
    assert saved.result is None
    assert saved.created_at is not None


@pytest.mark.django_db
def test_result_stores_json():
    created = IdempotencyRecord.objects.create(key="k", result={"rows": 3})
    saved = IdempotencyRecord.objects.get(id=created.id)
    assert saved.result == {"rows": 3}


@pytest.mark.django_db
def test_result_can_be_left_blank():
    IdempotencyRecord(key="k").full_clean()


@pytest.mark.django_db
def test_str_returns_key():
    assert str(IdempotencyRecord.objects.create(key="abc")) == "abc"


@pytest.mark.django_db
def test_key_length_and_blank_rules():
    IdempotencyRecord(key="k" * 200).full_clean()
    with pytest.raises(ValidationError):
        IdempotencyRecord(key="k" * 201).full_clean()
    with pytest.raises(ValidationError):
        IdempotencyRecord(key="").full_clean()


def test_record_has_exactly_the_specified_fields():
    names = {field.name for field in IdempotencyRecord._meta.concrete_fields}
    assert names == {"id", "key", "result", "created_at"}


def test_record_is_registered_in_admin():
    assert admin.site.is_registered(IdempotencyRecord)


@pytest.mark.django_db
def test_key_must_be_unique():
    IdempotencyRecord.objects.create(key="dup")
    with pytest.raises(IntegrityError):
        IdempotencyRecord.objects.create(key="dup")
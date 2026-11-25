import pytest
from rest_framework.test import APIClient

from engine.definition import validate_definition, validate_executors
from engine.executors import EXECUTORS, register
from engine.models import Run, Workflow
from engine.services import RunNotAllowed, create_run


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def clean_registry():
    snapshot = dict(EXECUTORS)
    yield
    EXECUTORS.clear()
    EXECUTORS.update(snapshot)


# ---------- validate_executors ----------

def test_validate_executors_accepts_builtin_fns():
    tasks = [
        {"name": "a", "fn": "echo"},
        {"name": "b", "fn": "sleep"},
        {"name": "c", "fn": "fail"},
        {"name": "d", "fn": "flaky"},
    ]
    assert validate_executors({"tasks": tasks}) == []


def test_validate_executors_rejects_unknown_fn():
    errors = validate_executors({"tasks": [{"name": "a", "fn": "nope"}]})
    assert errors
    assert any("'nope'" in message for message in errors)


def test_validate_executors_checks_every_task():
    tasks = [
        {"name": "a", "fn": "x1"},
        {"name": "b", "fn": "echo"},
        {"name": "c", "fn": "y1"},
    ]
    errors = validate_executors({"tasks": tasks})
    assert any("'x1'" in message for message in errors)
    assert any("'y1'" in message for message in errors)


def test_validate_executors_uses_the_live_registry(clean_registry):
    @register("t13_valid")
    def custom(task_run, sleep=None):
        return None

    assert validate_executors({"tasks": [{"name": "a", "fn": "t13_valid"}]}) == []


@pytest.mark.parametrize(
    "definition",
    [
        None,
        {"tasks": [{"name": "a"}]},
        {"tasks": [1, {"name": "b", "fn": ["echo"]}]},
    ],
    ids=["none", "missing-fn", "weird-shapes"],
)
def test_validate_executors_never_crashes_on_bad_shapes(definition):
    assert validate_executors(definition) == []


def test_validate_definition_does_not_check_the_registry():
    definition = {"tasks": [{"name": "a", "fn": "nope"}]}
    assert validate_definition(definition) == []


# ---------- API + service ----------

@pytest.mark.django_db
def test_api_post_unknown_fn_is_400(api):
    response = api.post(
        "/api/workflows/",
        {"name": "w", "definition": {"tasks": [{"name": "a", "fn": "nope"}]}},
        format="json",
    )
    assert response.status_code == 400
    messages = response.json()["definition"]
    assert any("'nope'" in message for message in messages)
    assert Workflow.objects.count() == 0


@pytest.mark.django_db
def test_api_post_builtin_fn_is_201(api):
    response = api.post(
        "/api/workflows/",
        {"name": "w", "definition": {"tasks": [{"name": "a", "fn": "echo"}]}},
        format="json",
    )
    assert response.status_code == 201
    assert Workflow.objects.count() == 1


@pytest.mark.django_db
def test_api_patch_unknown_fn_is_400_and_changes_nothing(api):
    wf = Workflow.objects.create(
        name="w", definition={"tasks": [{"name": "a", "fn": "echo"}]}
    )
    response = api.patch(
        f"/api/workflows/{wf.id}/",
        {"definition": {"tasks": [{"name": "a", "fn": "nope"}]}},
        format="json",
    )
    assert response.status_code == 400
    saved = Workflow.objects.get(id=wf.id)
    assert saved.definition == {"tasks": [{"name": "a", "fn": "echo"}]}
    assert saved.version == 1


@pytest.mark.django_db
def test_create_run_rejects_stored_unknown_fn():
    wf = Workflow.objects.create(
        name="old", definition={"tasks": [{"name": "a", "fn": "ghost"}]}
    )
    with pytest.raises(RunNotAllowed) as error:
        create_run(wf)
    assert str(error.value) == "Workflow definition is invalid."
    assert Run.objects.count() == 0
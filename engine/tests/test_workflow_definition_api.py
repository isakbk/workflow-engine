import pytest
from rest_framework.test import APIClient
from engine.models import Workflow

LIST_URL = "/api/workflows/"


def detail_url(pk):
    return f"/api/workflows/{pk}/"


def task(name, **extra):
    data = {"name": name, "fn": "echo"}
    data.update(extra)
    return data


def definition(*tasks):
    return {"tasks": list(tasks)}


def messages(response):
    return response.json()["definition"]


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def workflow():
    return Workflow.objects.create(name="flow", definition=definition(task("a")))


@pytest.mark.django_db
def test_create_with_valid_definition_returns_201(api):
    diamond = definition(
        task("extract"),
        task("clean", depends_on=["extract"]),
        task("stats", depends_on=["extract"]),
        task("report", depends_on=["clean", "stats"]),
    )
    response = api.post(LIST_URL, {"name": "etl", "definition": diamond}, format="json")
    assert response.status_code == 201
    assert Workflow.objects.get(name="etl").definition == diamond


@pytest.mark.django_db
def test_create_with_invalid_definition_returns_400_with_every_error(api):
    broken = definition(task("a", depends_on=["ghost"]), {"name": "b"})
    response = api.post(LIST_URL, {"name": "bad", "definition": broken}, format="json")
    assert response.status_code == 400
    errors = messages(response)
    assert isinstance(errors, list)
    assert len(errors) == 2
    assert any("ghost" in error for error in errors)
    assert Workflow.objects.count() == 0


@pytest.mark.django_db
def test_create_with_a_non_object_definition_returns_400(api):
    for bad in [[], "text", 5, {}, None]:
        response = api.post(LIST_URL, {"name": "n", "definition": bad}, format="json")
        assert response.status_code == 400
        assert "definition" in response.json()
    assert Workflow.objects.count() == 0


@pytest.mark.django_db
def test_create_without_definition_is_still_allowed(api):
    response = api.post(LIST_URL, {"name": "draft"}, format="json")
    assert response.status_code == 201
    assert response.json()["definition"] == {}


@pytest.mark.django_db
def test_create_with_a_cycle_returns_400(api):
    loop = definition(task("a", depends_on=["b"]), task("b", depends_on=["a"]))
    response = api.post(LIST_URL, {"name": "loop", "definition": loop}, format="json")
    assert response.status_code == 400
    errors = messages(response)
    assert any(" -> " in error and "a" in error and "b" in error for error in errors)
    assert Workflow.objects.count() == 0


@pytest.mark.django_db
def test_self_dependency_returns_400(api):
    selfish = definition(task("a", depends_on=["a"]))
    response = api.post(LIST_URL, {"name": "selfish", "definition": selfish}, format="json")
    assert response.status_code == 400
    assert any(" -> " in error for error in messages(response))


@pytest.mark.django_db
def test_cycle_message_shows_the_whole_path(api):
    loop = definition(
        task("x", depends_on=["y"]),
        task("y", depends_on=["z"]),
        task("z", depends_on=["x"]),
    )
    response = api.post(LIST_URL, {"name": "ring", "definition": loop}, format="json")
    assert response.status_code == 400
    errors = messages(response)
    assert len(errors) == 1
    assert errors[0].count(" -> ") == 3
    for name in ["x", "y", "z"]:
        assert name in errors[0]


@pytest.mark.django_db
def test_shape_errors_are_reported_without_a_cycle_check(api):
    mixed = definition(
        task("a", depends_on=["b"]),
        task("b", depends_on=["a"]),
        {"name": "c"},
    )
    response = api.post(LIST_URL, {"name": "mixed", "definition": mixed}, format="json")
    assert response.status_code == 400
    errors = messages(response)
    assert len(errors) == 1
    assert "fn" in errors[0]
    assert " -> " not in errors[0]


@pytest.mark.django_db
def test_put_with_invalid_definition_keeps_old_data(api, workflow):
    payload = {"name": "renamed", "definition": definition(task("a", depends_on=["ghost"]))}
    response = api.put(detail_url(workflow.id), payload, format="json")
    assert response.status_code == 400
    assert "definition" in response.json()
    workflow.refresh_from_db()
    assert workflow.name == "flow"
    assert workflow.definition == definition(task("a"))
    assert workflow.version == 1


@pytest.mark.django_db
def test_patch_with_a_cycle_returns_400_and_keeps_old_data(api, workflow):
    loop = definition(task("a", depends_on=["b"]), task("b", depends_on=["a"]))
    response = api.patch(detail_url(workflow.id), {"definition": loop}, format="json")
    assert response.status_code == 400
    workflow.refresh_from_db()
    assert workflow.definition == definition(task("a"))
    assert workflow.version == 1


@pytest.mark.django_db
def test_patch_without_definition_skips_validation(api):
    draft = Workflow.objects.create(name="draft")
    response = api.patch(detail_url(draft.id), {"is_active": False}, format="json")
    assert response.status_code == 200


@pytest.mark.django_db
def test_version_is_one_on_create(api):
    payload = {"name": "v", "definition": definition(task("a"))}
    response = api.post(LIST_URL, payload, format="json")
    assert response.status_code == 201
    assert response.json()["version"] == 1


@pytest.mark.django_db
def test_version_increases_with_each_definition_change(api, workflow):
    first = definition(task("a"), task("b"))
    second = definition(task("a"), task("b"), task("c"))
    response = api.patch(detail_url(workflow.id), {"definition": first}, format="json")
    assert response.status_code == 200
    assert response.json()["version"] == 2
    response = api.patch(detail_url(workflow.id), {"definition": second}, format="json")
    assert response.json()["version"] == 3
    workflow.refresh_from_db()
    assert workflow.version == 3


@pytest.mark.django_db
def test_version_stays_when_definition_is_the_same(api, workflow):
    response = api.patch(
        detail_url(workflow.id), {"definition": definition(task("a"))}, format="json"
    )
    assert response.status_code == 200
    workflow.refresh_from_db()
    assert workflow.version == 1


@pytest.mark.django_db
def test_version_stays_when_other_fields_change(api, workflow):
    payload = {"name": "other", "cron": "0 1 * * *", "is_active": False}
    response = api.patch(detail_url(workflow.id), payload, format="json")
    assert response.status_code == 200
    workflow.refresh_from_db()
    assert workflow.version == 1


@pytest.mark.django_db
def test_put_with_a_new_definition_increases_version(api, workflow):
    payload = {"name": "flow", "definition": definition(task("a"), task("b"))}
    response = api.put(detail_url(workflow.id), payload, format="json")
    assert response.status_code == 200
    assert response.json()["version"] == 2


@pytest.mark.django_db
def test_first_definition_of_a_draft_does_not_bump_version(api):
    draft = Workflow.objects.create(name="draft")
    response = api.patch(
        detail_url(draft.id), {"definition": definition(task("a"))}, format="json"
    )
    assert response.status_code == 200
    draft.refresh_from_db()
    assert draft.version == 1


@pytest.mark.django_db
def test_valid_definition_is_stored_exactly_as_sent(api, workflow):
    payload = definition(
        task("a"),
        task("b", depends_on=["a"], max_attempts=2, timeout_seconds=30),
    )
    response = api.patch(detail_url(workflow.id), {"definition": payload}, format="json")
    assert response.status_code == 200
    workflow.refresh_from_db()
    assert workflow.definition == payload
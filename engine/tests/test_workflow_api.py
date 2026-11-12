import pytest
from rest_framework.test import APIClient
from engine.models import Workflow

LIST_URL = "/api/workflows/"
FIELDS = {"id", "name", "definition", "cron", "is_active", "version", "created_at"}


def detail_url(pk):
    return f"/api/workflows/{pk}/"


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_list_is_empty_at_start(api):
    response = api.get(LIST_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_list_returns_workflows_ordered_by_id(api):
    for name in ["b_flow", "a_flow", "c_flow"]:
        Workflow.objects.create(name=name)
    response = api.get(LIST_URL)
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["b_flow", "a_flow", "c_flow"]


@pytest.mark.django_db
def test_list_item_has_exactly_the_specified_fields(api):
    Workflow.objects.create(name="one")
    item = api.get(LIST_URL).json()[0]
    assert set(item.keys()) == FIELDS


@pytest.mark.django_db
def test_create_returns_201_with_defaults(api):
    response = api.post(LIST_URL, {"name": "daily"}, format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == "daily"
    assert body["definition"] == {}
    assert body["cron"] == ""
    assert body["is_active"] is True
    assert body["version"] == 1
    assert Workflow.objects.count() == 1


@pytest.mark.django_db
def test_create_stores_all_writable_fields(api):
    payload = {
        "name": "nightly",
        "definition": {"tasks": [{"name": "a", "fn": "echo", "depends_on": []}]},
        "cron": "0 2 * * *",
        "is_active": False,
    }
    response = api.post(LIST_URL, payload, format="json")
    assert response.status_code == 201
    saved = Workflow.objects.get(name="nightly")
    assert saved.definition == payload["definition"]
    assert saved.cron == "0 2 * * *"
    assert saved.is_active is False


@pytest.mark.django_db
def test_create_ignores_version_and_id(api):
    response = api.post(LIST_URL, {"name": "x", "version": 5, "id": 999}, format="json")
    assert response.status_code == 201
    assert response.json()["version"] == 1
    assert response.json()["id"] != 999


@pytest.mark.django_db
def test_create_with_invalid_name_returns_400(api):
    for payload in [{}, {"name": ""}, {"name": "x" * 101}]:
        response = api.post(LIST_URL, payload, format="json")
        assert response.status_code == 400
        assert "name" in response.json()
    assert Workflow.objects.count() == 0


@pytest.mark.django_db
def test_create_with_duplicate_name_returns_400(api):
    Workflow.objects.create(name="dup")
    response = api.post(LIST_URL, {"name": "dup"}, format="json")
    assert response.status_code == 400
    assert "name" in response.json()
    assert Workflow.objects.count() == 1


@pytest.mark.django_db
def test_create_with_invalid_cron_or_is_active_returns_400(api):
    for field, value in [("cron", "c" * 51), ("is_active", "maybe")]:
        response = api.post(LIST_URL, {"name": "n", field: value}, format="json")
        assert response.status_code == 400
        assert field in response.json()


@pytest.mark.django_db
def test_retrieve_returns_the_workflow(api):
    workflow = Workflow.objects.create(name="one", cron="0 1 * * *")
    response = api.get(detail_url(workflow.id))
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == FIELDS
    assert body["id"] == workflow.id
    assert body["name"] == "one"
    assert body["cron"] == "0 1 * * *"


@pytest.mark.django_db
def test_retrieve_missing_workflow_returns_404(api):
    assert api.get(detail_url(9999)).status_code == 404


@pytest.mark.django_db
def test_put_replaces_the_workflow(api):
    workflow = Workflow.objects.create(name="old", cron="0 1 * * *")
    payload = {"name": "new", "definition": {"tasks": []}, "cron": "", "is_active": False}
    response = api.put(detail_url(workflow.id), payload, format="json")
    assert response.status_code == 200
    workflow.refresh_from_db()
    assert workflow.name == "new"
    assert workflow.definition == {"tasks": []}
    assert workflow.cron == ""
    assert workflow.is_active is False
    assert workflow.version == 1


@pytest.mark.django_db
def test_put_without_name_returns_400(api):
    workflow = Workflow.objects.create(name="old")
    response = api.put(detail_url(workflow.id), {"cron": ""}, format="json")
    assert response.status_code == 400
    assert "name" in response.json()


@pytest.mark.django_db
def test_put_missing_workflow_returns_404(api):
    assert api.put(detail_url(9999), {"name": "x"}, format="json").status_code == 404


@pytest.mark.django_db
def test_patch_updates_only_the_sent_fields(api):
    workflow = Workflow.objects.create(name="keep", cron="0 1 * * *")
    response = api.patch(detail_url(workflow.id), {"is_active": False}, format="json")
    assert response.status_code == 200
    workflow.refresh_from_db()
    assert workflow.is_active is False
    assert workflow.name == "keep"
    assert workflow.cron == "0 1 * * *"


@pytest.mark.django_db
def test_patch_cannot_change_version(api):
    workflow = Workflow.objects.create(name="v")
    response = api.patch(detail_url(workflow.id), {"version": 9}, format="json")
    assert response.status_code == 200
    workflow.refresh_from_db()
    assert workflow.version == 1


@pytest.mark.django_db
def test_patch_to_a_duplicate_name_returns_400(api):
    Workflow.objects.create(name="other")
    workflow = Workflow.objects.create(name="mine")
    response = api.patch(detail_url(workflow.id), {"name": "other"}, format="json")
    assert response.status_code == 400
    assert "name" in response.json()
    workflow.refresh_from_db()
    assert workflow.name == "mine"


@pytest.mark.django_db
def test_patch_with_its_own_name_is_ok(api):
    workflow = Workflow.objects.create(name="mine")
    response = api.patch(detail_url(workflow.id), {"name": "mine"}, format="json")
    assert response.status_code == 200


@pytest.mark.django_db
def test_delete_removes_the_workflow(api):
    workflow = Workflow.objects.create(name="gone")
    response = api.delete(detail_url(workflow.id))
    assert response.status_code == 204
    assert Workflow.objects.count() == 0
    assert api.get(detail_url(workflow.id)).status_code == 404


@pytest.mark.django_db
def test_delete_missing_workflow_returns_404(api):
    assert api.delete(detail_url(9999)).status_code == 404


@pytest.mark.django_db
def test_unsupported_methods_return_405(api):
    workflow = Workflow.objects.create(name="one")
    assert api.delete(LIST_URL).status_code == 405
    assert api.put(LIST_URL, {}, format="json").status_code == 405
    assert api.post(detail_url(workflow.id), {}, format="json").status_code == 405
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def valid_workflow():
    return {
        "name": "test_workflow",
        "definition": {
            "tasks": [
                {
                    "name": "test_task",
                    "fn": "test_fn",
                    "depends_on": [],
                }
            ]
        },
        "cron": "* * * * *",
        "is_active": True,
        "version": 1,
    }


@pytest.mark.django_db
def test_create_workflow_returns_201(api_client, valid_workflow):
    response = api_client.post(
        "/api/workflow/",
        valid_workflow,
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_create_workflow_with_cycle_returns_400(api_client, valid_workflow):
    valid_workflow["name"] = "cyclic_workflow"
    valid_workflow["definition"]["tasks"] = [
        {
            "name": "A",
            "fn": "function_a",
            "depends_on": ["B"],
        },
        {
            "name": "B",
            "fn": "function_b",
            "depends_on": ["A"],
        },
    ]

    response = api_client.post(
        "/api/workflow/",
        valid_workflow,
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_create_duplicate_name_returns_400(api_client, valid_workflow):
    first_response = api_client.post(
        "/api/workflow/",
        valid_workflow,
        format="json",
    )

    assert first_response.status_code == 201

    duplicate_response = api_client.post(
        "/api/workflow/",
        valid_workflow,
        format="json",
    )

    assert duplicate_response.status_code == 400


@pytest.mark.django_db
def test_list_workflows(api_client, valid_workflow):
    create_response = api_client.post(
        "/api/workflow/",
        valid_workflow,
        format="json",
    )

    assert create_response.status_code == 201

    response = api_client.get("/api/workflow/")

    assert response.status_code == 200

    # Check that the created workflow appears in the list.
    results = response.data
    if isinstance(results, dict) and "results" in results:
        results = results["results"]

    assert any(workflow["name"] == "test_workflow" for workflow in results)


@pytest.mark.django_db
def test_get_workflow_by_id_returns_200(api_client, valid_workflow):
    # Create a workflow first
    create_response = api_client.post(
        "/api/workflow/",
        valid_workflow,
        format="json",
    )
    assert create_response.status_code == 201
    workflow_id = create_response.data["id"]

    # Get the workflow by id
    response = api_client.get(f"/api/workflows/{workflow_id}/")
    assert response.status_code == 200
    assert response.data["name"] == valid_workflow["name"]
    assert response.data["definition"] == valid_workflow["definition"]


@pytest.mark.django_db
def test_get_workflow_has_expected_fields(api_client, valid_workflow):
    # Create a workflow first
    create_response = api_client.post(
        "/api/workflow/",
        valid_workflow,
        format="json",
    )
    assert create_response.status_code == 201
    workflow_id = create_response.data["id"]

    # Get the workflow by id
    response = api_client.get(f"/api/workflows/{workflow_id}/")
    assert response.status_code == 200
    expected_fields = {
        "id",
        "name",
        "definition",
        "cron",
        "is_active",
        "version",
        "created_at",
    }
    assert set(response.data.keys()) == expected_fields


@pytest.mark.django_db
def test_get_missing_workflow_returns_404(api_client):
    # Try to get a workflow that doesn't exist
    response = api_client.get("/api/workflows/9999/")
    assert response.status_code == 404

import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient

from engine.models import Run, TaskRun, Workflow
from engine.services import RunNotAllowed, create_run
from engine.views import CreateRunView

@pytest.fixture
def api():
    return APIClient()


def make_workflow(name="etl", tasks=None, is_active=True):
    if tasks is None:
        tasks = [
            {"name": "extract", "fn": "echo"},
            {"name": "transform", "fn": "echo", "depends_on": ["extract"]},
            {"name": "load", "fn": "echo", "depends_on": ["transform"]},
        ]
    return Workflow.objects.create(
        name=name, definition={"tasks": tasks}, is_active=is_active
    )


# ---------- service: create_run ----------

@pytest.mark.django_db
def test_create_run_makes_pending_manual_run():
    wf = make_workflow()
    run = create_run(wf)
    assert isinstance(run, Run)
    assert run.workflow == wf
    assert run.status == "PENDING"
    assert run.trigger == "MANUAL"
    assert run.started_at is None
    assert run.finished_at is None
    assert Run.objects.count() == 1


@pytest.mark.django_db
def test_create_run_accepts_cron_trigger():
    wf = make_workflow()
    run = create_run(wf, trigger="CRON")
    assert run.trigger == "CRON"


@pytest.mark.django_db
def test_create_run_makes_one_pending_task_run_per_task():
    wf = make_workflow()
    run = create_run(wf)
    names = list(run.task_runs.order_by("id").values_list("name", flat=True))
    assert names == ["extract", "transform", "load"]
    for task_run in run.task_runs.all():
        assert task_run.status == "PENDING"
        assert task_run.attempt == 0


@pytest.mark.django_db
def test_create_run_copies_fn_and_depends_on():
    wf = make_workflow(
        tasks=[
            {"name": "a", "fn": "echo"},
            {"name": "b", "fn": "sleep", "depends_on": ["a"]},
        ]
    )
    run = create_run(wf)
    by_name = {t.name: t for t in run.task_runs.all()}
    assert by_name["a"].fn == "echo"
    assert by_name["a"].depends_on == []
    assert by_name["b"].fn == "sleep"
    assert by_name["b"].depends_on == ["a"]


@pytest.mark.django_db
def test_create_run_uses_task_values_or_model_defaults():
    wf = make_workflow(
        tasks=[
            {"name": "a", "fn": "echo", "max_attempts": 5, "timeout_seconds": 120},
            {"name": "b", "fn": "echo"},
        ]
    )
    run = create_run(wf)
    by_name = {t.name: t for t in run.task_runs.all()}
    assert by_name["a"].max_attempts == 5
    assert by_name["a"].timeout_seconds == 120
    assert by_name["b"].max_attempts == 3
    assert by_name["b"].timeout_seconds == 60


@pytest.mark.django_db
def test_create_run_builds_idempotency_keys():
    wf = make_workflow()
    run = create_run(wf)
    keys = set(run.task_runs.values_list("idempotency_key", flat=True))
    assert keys == {
        f"run-{run.id}:extract",
        f"run-{run.id}:transform",
        f"run-{run.id}:load",
    }


@pytest.mark.django_db
def test_two_runs_of_same_workflow_do_not_clash():
    wf = make_workflow()
    first = create_run(wf)
    second = create_run(wf)
    assert first.id != second.id
    assert Run.objects.count() == 2
    assert TaskRun.objects.count() == 6
    assert len(set(TaskRun.objects.values_list("idempotency_key", flat=True))) == 6


@pytest.mark.django_db
def test_inactive_workflow_is_rejected():
    wf = make_workflow(is_active=False)
    with pytest.raises(RunNotAllowed) as error:
        create_run(wf)
    assert str(error.value) == "Workflow is inactive."
    assert Run.objects.count() == 0
    assert TaskRun.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("definition", [{}, {"tasks": []}])
def test_workflow_without_tasks_is_rejected(definition):
    wf = Workflow.objects.create(name="empty", definition=definition)
    with pytest.raises(RunNotAllowed) as error:
        create_run(wf)
    assert str(error.value) == "Workflow has no tasks."
    assert Run.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tasks",
    [
        [{"name": "a"}],
        [
            {"name": "a", "fn": "echo", "depends_on": ["b"]},
            {"name": "b", "fn": "echo", "depends_on": ["a"]},
        ],
    ],
    ids=["missing-fn", "cycle"],
)
def test_invalid_definition_is_rejected(tasks):
    wf = make_workflow(name="bad", tasks=tasks)
    with pytest.raises(RunNotAllowed) as error:
        create_run(wf)
    assert str(error.value) == "Workflow definition is invalid."
    assert Run.objects.count() == 0
    assert TaskRun.objects.count() == 0


@pytest.mark.django_db
def test_failure_while_creating_task_runs_rolls_back_everything():
    wf = make_workflow()
    old_run = Run.objects.create(workflow=wf)
    # the next Run will get id old_run.id + 1, so its "transform" key already exists
    TaskRun.objects.create(
        run=old_run,
        name="old",
        fn="echo",
        idempotency_key=f"run-{old_run.id + 1}:transform",
    )
    with pytest.raises(IntegrityError):
        create_run(wf)
    # exception to the "IntegrityError last" rule: here checking AFTER is the whole point
    assert Run.objects.count() == 1
    assert TaskRun.objects.count() == 1


# ---------- API ----------

@pytest.mark.django_db
def test_post_run_returns_201_with_run_and_task_runs(api):
    wf = make_workflow()
    response = api.post(f"/api/workflows/{wf.id}/run/")
    assert response.status_code == 201
    body = response.json()
    run = Run.objects.get()
    assert body["id"] == run.id
    assert body["workflow"] == wf.id
    assert body["status"] == "PENDING"
    assert body["trigger"] == "MANUAL"
    assert body["started_at"] is None
    assert body["finished_at"] is None
    assert [t["name"] for t in body["task_runs"]] == ["extract", "transform", "load"]
    assert body["task_runs"][1]["depends_on"] == ["extract"]
    wanted = {
        "id", "name", "fn", "depends_on", "status",
        "attempt", "max_attempts", "timeout_seconds",
    }
    for item in body["task_runs"]:
        assert wanted <= set(item)
        assert item["status"] == "PENDING"


@pytest.mark.django_db
def test_post_run_saves_rows(api):
    wf = make_workflow()
    api.post(f"/api/workflows/{wf.id}/run/")
    assert Run.objects.count() == 1
    assert TaskRun.objects.count() == 3


@pytest.mark.django_db
def test_post_run_unknown_workflow_is_404(api):
    response = api.post("/api/workflows/99999/run/")
    assert response.status_code == 404
    assert Run.objects.count() == 0


@pytest.mark.django_db
def test_post_run_inactive_is_400(api):
    wf = make_workflow(is_active=False)
    response = api.post(f"/api/workflows/{wf.id}/run/")
    assert response.status_code == 400
    assert response.json() == {"detail": "Workflow is inactive."}
    assert Run.objects.count() == 0


@pytest.mark.django_db
def test_post_run_without_tasks_is_400(api):
    wf = Workflow.objects.create(name="empty")
    response = api.post(f"/api/workflows/{wf.id}/run/")
    assert response.status_code == 400
    assert response.json() == {"detail": "Workflow has no tasks."}
    assert Run.objects.count() == 0


@pytest.mark.django_db
def test_post_run_invalid_definition_is_400(api):
    wf = make_workflow(name="bad", tasks=[{"name": "a"}])
    response = api.post(f"/api/workflows/{wf.id}/run/")
    assert response.status_code == 400
    assert response.json() == {"detail": "Workflow definition is invalid."}
    assert Run.objects.count() == 0
    assert TaskRun.objects.count() == 0


@pytest.mark.django_db
def test_get_on_run_url_is_405(api):
    wf = make_workflow()
    response = api.get(f"/api/workflows/{wf.id}/run/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_post_run_twice_creates_two_runs(api):
    wf = make_workflow()
    first = api.post(f"/api/workflows/{wf.id}/run/")
    second = api.post(f"/api/workflows/{wf.id}/run/")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert Run.objects.count() == 2
    assert TaskRun.objects.count() == 6
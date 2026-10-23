from engine.models import Workflow
from django.db import IntegrityError, transaction
import pytest

def test_workflow_model(db):
    Workflow.objects.create(
        name="task",
        definition={"name":"task","function":"task_fn","dependancy":[]},
        cron="* * * * * 0",
        is_active=True
    )

    name=Workflow.objects.get(name="task")
    assert name.name == "task"
    assert name.definition == {"name":"task","function":"task_fn","dependancy":[]}
    assert name.cron == "* * * * * 0"
    assert name.is_active == True
    assert name.created_at is not None

def test_workflow_name_is_unique(db):
    Workflow.objects.create(
        name="task",
        definition={"name":"task","function":"task_fn","dependancy":[]},
        cron="* * * * * 0",
        is_active=True
    ) 

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Workflow.objects.create(
                name="task",
                definition={"name":"task","function":"task_fn","dependancy":[]},
                cron="* * * * * 0",
                is_active=True
            )


    
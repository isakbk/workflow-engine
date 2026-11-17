from rest_framework.views import APIView
from rest_framework.response import Response
from engine.models import Workflow
from engine.serializers import WorkflowSerializer
from django.shortcuts import get_object_or_404
from rest_framework import status


from engine.models import Workflow
from engine.services import create_run, RunNotAllowed


class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


# id, name, definition, cron, is_active, version
class WorkflowView(APIView):
    def post(self, request, id=None):
        if id is not None:
            return Response(status=405)
        workflow_serializer = WorkflowSerializer(data=request.data)
        if workflow_serializer.is_valid():
            workflow_serializer.save()
            return Response(workflow_serializer.data, status=201)
        return Response(workflow_serializer.errors, status=400)

    def get(self, request, id=None):
        if id is not None:
            workflow = get_object_or_404(Workflow, id=id)
            serializer = WorkflowSerializer(workflow)
            return Response(serializer.data)

        workflows = Workflow.objects.all().order_by("id")
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data)

    def put(self, request, id=None):
        if id is None:
            return Response(status=405)

        workflow = get_object_or_404(Workflow, id=id)

        serializer = WorkflowSerializer(workflow, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    def patch(self, request, id):
        workflow = get_object_or_404(Workflow, id=id)
        workflow_serializer = WorkflowSerializer(
            workflow, data=request.data, partial=True
        )
        if workflow_serializer.is_valid():
            workflow_serializer.save()
            return Response(workflow_serializer.data, status=200)
        return Response(workflow_serializer.errors, status=400)

    def delete(self, request, id=None):
        if id is None:
            return Response(status=405)

        workflow = get_object_or_404(Workflow, id=id)
        workflow.delete()

        return Response(status=204)


class CreateRunView(APIView):
    def post(self, request, workflow_id):
        workflow = get_object_or_404(Workflow, id=workflow_id)

        try:
            run = create_run(workflow)

        except RunNotAllowed as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        task_runs = run.task_runs.order_by("id")

        response_data = {
            "id": run.id,
            "workflow": run.workflow_id,
            "status": run.status,
            "trigger": run.trigger,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "task_runs": [
                {
                    "id": task.id,
                    "name": task.name,
                    "fn": task.fn,
                    "depends_on": task.depends_on,
                    "status": task.status,
                    "attempt": task.attempt,
                    "max_attempts": task.max_attempts,
                    "timeout_seconds": task.timeout_seconds,
                }
                for task in task_runs
            ],
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

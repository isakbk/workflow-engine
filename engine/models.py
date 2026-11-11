from enum import unique
from socket import timeout
from django.db import models
from django.db.models.functions.datetime import TruncWeek

class Workflow(models.Model):
    name=models.CharField(max_length=100, unique=True)
    definition=models.JSONField(default=dict)
    cron=models.CharField(max_length=50, blank=True)
    is_active=models.BooleanField(default=True)
    version=models.IntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name

status_choices_list=[
    ("PENDING", "Pending"), 
    ("RUNNING", "Running"), 
    ("SUCCESS", "sucess"), 
    ("FAILED", "Failed"), 
    ("CANCELLED", "Cancelled")
]
trigger_choices_list=[("MANUAL","manual"),("CRON",("cron"))]

class Run(models.Model):
    workflow=models.ForeignKey(Workflow, on_delete=models.CASCADE,related_name="runs")
    status=models.CharField(max_length=50, choices=status_choices_list,default="PENDING")
    trigger=models.CharField(max_length=10,choices=trigger_choices_list,default="MANUAL")
    created_at=models.DateTimeField(auto_now_add=True)
    started_at=models.DateTimeField(null=True, blank=True)
    finished_at=models.DateTimeField(null=True, blank=True)


    def __str__(self):
     return f"Run #{self.id} of {self.workflow.name}"
values = [("PENDING", "PENDING"), ("QUEUED", "QUEUED"), ("RUNNING", "RUNNING"), ("SUCCESS", "SUCCESS"), ("FAILED", "FAILED"),
              ("RETRYING", "RETRYING"), ("DEAD", "DEAD"), ("SKIPPED", "SKIPPED"), ("CANCELLED", "CANCELLED")]
class TaskRun(models.Model):
    run=models.ForeignKey("RUN", on_delete=models.CASCADE, related_name="task_runs")
    name=models.CharField(max_length=100)
    fn=models.CharField(max_length=100)
    depends_on=models.JSONField(default=list, blank=True)
    status=models.CharField(max_length=20, choices=values, default="PENDING")
    attempt=models.PositiveIntegerField(default=0)
    max_attempts=models.PositiveIntegerField(default=3)
    timeout_seconds=models.PositiveIntegerField(default=60)
    next_retry_at=models.DateTimeField(null=True, blank=True)
    last_heartbeat=models.DateTimeField(null=True, blank=True)
    worker_id=models.CharField(max_length=100, default="", blank=True)
    idempotency_key=models.CharField(max_length=200, unique=True)
    output=models.JSONField(default=None, blank=True, null=True)
    error=models.TextField(default="", blank=True)
    started_at=models.DateTimeField(default=None, null=True, blank=True)
    finished_at=models.DateTimeField(default=None, null=True, blank=True)
    

    TERMINAL = {"SUCCESS", "DEAD", "SKIPPED", "CANCELLED"}

    # Your existing fields...

    class Meta:
      constraints = [
        models.UniqueConstraint(
            fields=["run", "name"],
            name="unique_task_per_run"
        )
    ]

      indexes = [
        models.Index(
            fields=["status", "next_retry_at"],
            name="task_status_retry_idx"
        ),
        models.Index(
            fields=["status", "last_heartbeat"],
            name="task_status_heartbeat_idx"
        ),
        models.Index(
            fields=["run", "status"],
            name="task_run_status_idx"
        ),
    ]

    def __str__(self):
        return f"Run #{self.run.id}: {self.name}"


class Attempt(models.Model):
    task_run = models.ForeignKey("TaskRun", on_delete=models.CASCADE, related_name="attempts")
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=[("SUCCESS", "SUCCESS"), ("FAILED", "FAILED")])
    worker_id =models.CharField(max_length=100)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(blank=True, null=True)
    error=models.TextField(default="", blank=True) 

    class Meta:
      constraints = [
        models.UniqueConstraint(
            fields=["task_run", "number"],
            name="unique_attempt_number_per_task"
             )
        ]

      ordering = ["number"]
    
    def __str__(self):
     return f"{self.task_run.name} - Attempt {self.number}"


class IdempotencyRecord(models.Model):
    key = models.CharField(max_length=200, unique=True)
    result = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.key
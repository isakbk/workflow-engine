from enum import unique
from django.db import models

class Workflow(models.Model):
    name=models.CharField(max_length=100, unique=True)
    definition=models.JSONField(default=dict)
    cron=models.CharField(max_length=50, blank=True)
    is_active=models.BooleanField(default=True)
    version=models.IntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name

status_choices_list=[("PENDING", "Pending"), ("RUNNING", "Running"), ("SUCCESS", "sucess"), ("FAILED", "Failed"), ("CANCELLED", "Cancelled")]
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


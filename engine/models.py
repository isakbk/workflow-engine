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
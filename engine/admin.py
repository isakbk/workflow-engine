from django.contrib import admin
from engine.models import Workflow,Run,TaskRun,IdempotencyRecord,Attempt
# Register your models here.

admin.site.register(Workflow)
admin.site.register(Run)
admin.site.register(TaskRun)
admin.site.register(IdempotencyRecord)
admin.site.register(Attempt)

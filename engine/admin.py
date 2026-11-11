from django.contrib import admin
from engine.models import Workflow,Run,TaskRun
# Register your models here.

admin.site.register(Workflow)
admin.site.register(Run)
admin.site.register(TaskRun)



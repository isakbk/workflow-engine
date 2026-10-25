from django.urls import path
from . import views


urlpatterns = [
    path("", views.WorkflowEngineAPIView.as_view(), name="workflow-engine"),
    path("api/workflow/", views.WorkflowAPIView.as_view(), name="workflow-api"),
]

from django.urls import path
from . import views


urlpatterns = [
    path('', views.WorkflowEngineAPIView.as_view(), name='workflow-engine'),
]





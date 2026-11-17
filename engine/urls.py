from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.HealthCheckView.as_view(), name='health_check'),

    path('workflows/', views.WorkflowView.as_view(), name='workflows'),

    path('workflows/<int:id>/', views.WorkflowView.as_view(), name='workflow'),

    path(
        'workflows/<int:workflow_id>/run/',
        views.CreateRunView.as_view(),
        name='create-run'
    ),
]
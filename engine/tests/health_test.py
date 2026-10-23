from engine.views import WorkflowEngineAPIView
import pytest
def test_health():
    view = WorkflowEngineAPIView()
    response= view.get(None)
    assert response.status_code==200
    assert response.data=={"message":"ok"}
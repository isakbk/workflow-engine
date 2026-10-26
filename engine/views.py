from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from .models import Workflow
from .serializers import WorkflowSerializer

# Create your views here.


class WorkflowEngineAPIView(APIView):
    def get(self, request):
        return Response({"message": "ok"})


class WorkflowAPIView(APIView):
    def get(self, request):
        workflows = Workflow.objects.all()
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = WorkflowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkflowDetailView(RetrieveAPIView):
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer

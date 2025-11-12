from django.urls import path
from . import views

urlpatterns = [
    path("", views.kanoodle_solver, name="index"),
    path('api/solve/<int:solution_id>/', views.solvePartialSolution, name='solve_api'),
    path('api/pieces/', views.getPiecesApi, name='pieces_api'),
]
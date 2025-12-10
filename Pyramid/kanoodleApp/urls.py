from django.urls import path
from . import views

urlpatterns = [
    path("", views.pyramid_solver, name="index"),
    path("pyramid/", views.pyramid_solver, name="pyramid"),
    path('api/solve/<int:solution_id>/', views.solvePartialSolution, name='solve_api'),
    path('api/solve/<str:solution_id>/', views.solve_pyramid, name='pyramid_solve_api'),
    path('api/pieces/', views.getPiecesApi, name='pieces_api'),
]
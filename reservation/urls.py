from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('survey/', views.survey_page, name='survey_page'),
    path('submit-taste/', views.submit_taste, name='submit_taste'),
]
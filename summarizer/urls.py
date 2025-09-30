from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_emails, name='upload'),
    path('results/<int:summary_id>/', views.results_view, name='results'),
    path('api/summarize/', views.api_summarize, name='api_summarize'),
]
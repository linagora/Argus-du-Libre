"""URL configuration for the public app."""

from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("", views.home, name="home"),
    path("project/<slug:slug>/", views.project_detail, name="project_detail"),
    path("tag/<slug:slug>/", views.tag_detail, name="tag_detail"),
]

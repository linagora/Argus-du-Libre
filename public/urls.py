"""URL configuration for the public app."""

from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("help/scores/", views.scores_help, name="scores_help"),
    path("search/", views.search, name="search"),
    path("compare/", views.compare, name="compare"),
    path("project/<slug:slug>/", views.project_detail, name="project_detail"),
    path(
        "project/<slug:slug>/cost-feedback/",
        views.create_cost_feedback,
        name="create_cost_feedback",
    ),
    path(
        "project/<slug:software_slug>/field/<slug:field_slug>/",
        views.field_metrics,
        name="field_metrics",
    ),
    path("tags/", views.tags_list, name="tags_list"),
    path("tag/<slug:slug>/", views.tag_detail, name="tag_detail"),
]

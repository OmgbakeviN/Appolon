from django.urls import path
from . import views

app_name = "downloader"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("select/<str:video_id>/", views.select_video, name="select_video"),
    path("options/", views.options, name="options"),
    path("download/", views.download_media,name="download"),
    path("history/", views.history, name="history"),
    path("signup/", views.signup, name="signup"),
]
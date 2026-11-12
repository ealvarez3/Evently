from django.urls import path

from . import views

urlpatterns = [
    path("", views.invitation, name="home"),
    path("fiesta.ics", views.calendar, name="calendar"),
    path("i/<str:token>/", views.invitation, name="invitation"),
    path("i/<str:token>/asistencia/", views.rsvp, name="rsvp"),
    path("i/<str:token>/cancion/", views.song, name="song"),
    path("i/<str:token>/fotos/", views.vault_upload, name="vault_upload"),
]

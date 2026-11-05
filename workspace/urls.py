from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("entries/", views.entry_list, name="entry_list"),
    path("entries/new/", views.entry_create, name="entry_create"),
    path("entries/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("entries/<int:pk>/delete/", views.entry_delete, name="entry_delete"),
    path("backups/", views.backup_center, name="backup_center"),
    path("backups/create/", views.create_backup, name="create_backup"),
    path("backups/<int:pk>/download/", views.download_backup, name="download_backup"),
    path("backups/restore/", views.restore_backup, name="restore_backup"),
]

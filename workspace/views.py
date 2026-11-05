import os
import sqlite3
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connections
from django.http import FileResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EntryForm
from .models import BackupLog, Entry


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    entries = Entry.objects.filter(created_by=request.user)
    context = {
        "entry_count": entries.count(),
        "recent_entries": entries[:5],
        "backup_count": BackupLog.objects.filter(performed_by=request.user, action="created").count(),
    }
    return render(request, "workspace/dashboard.html", context)


@login_required
def entry_list(request):
    return render(request, "workspace/entry_list.html", {
        "entries": Entry.objects.filter(created_by=request.user)
    })


@login_required
def entry_create(request):
    form = EntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.created_by = request.user
        entry.save()
        messages.success(request, "Record created.")
        return redirect("entry_list")
    return render(request, "workspace/entry_form.html", {"form": form, "page_title": "New record"})


@login_required
def entry_edit(request, pk):
    entry = get_object_or_404(Entry, pk=pk, created_by=request.user)
    form = EntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Record updated.")
        return redirect("entry_list")
    return render(request, "workspace/entry_form.html", {"form": form, "page_title": "Edit record"})


@login_required
@require_POST
def entry_delete(request, pk):
    entry = get_object_or_404(Entry, pk=pk, created_by=request.user)
    entry.delete()
    messages.success(request, "Record deleted.")
    return redirect("entry_list")


def _sqlite_path():
    database = settings.DATABASES["default"]
    if database["ENGINE"] != "django.db.backends.sqlite3":
        raise ValidationError("This starter's built-in backup utility currently supports SQLite databases only.")
    return Path(database["NAME"])


def _backup_dir():
    directory = settings.BASE_DIR / "backups"
    directory.mkdir(exist_ok=True)
    return directory


@login_required
def backup_center(request):
    logs = BackupLog.objects.filter(performed_by=request.user)[:20]
    return render(request, "workspace/backup_center.html", {"logs": logs})


@login_required
@require_POST
def create_backup(request):
    destination = None
    try:
        source_path = _sqlite_path()
        if not source_path.exists():
            messages.error(request, "Database file was not found. Run migrations first.")
            return redirect("backup_center")

        stamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        filename = f"database-backup-{stamp}.sqlite3"
        destination = _backup_dir() / filename

        source = sqlite3.connect(str(source_path), timeout=20)
        target = sqlite3.connect(str(destination))
        try:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            target.close()
            source.close()

        if integrity != "ok":
            destination.unlink(missing_ok=True)
            messages.error(request, "Backup integrity check failed.")
            return redirect("backup_center")

        BackupLog.objects.create(
            filename=filename, action="created",
            file_size=destination.stat().st_size, performed_by=request.user
        )
        messages.success(request, f"Backup created: {filename}")
    except (OSError, sqlite3.Error, ValidationError, DatabaseError) as exc:
        if destination and destination.exists():
            destination.unlink(missing_ok=True)
        messages.error(request, f"Backup failed: {exc}")
    return redirect("backup_center")


@login_required
def download_backup(request, pk):
    log = get_object_or_404(BackupLog, pk=pk, performed_by=request.user, action="created")
    safe_filename = Path(log.filename).name
    backup_dir = _backup_dir().resolve()
    path = (backup_dir / safe_filename).resolve()
    if not path.is_relative_to(backup_dir) or not path.exists():
        messages.error(request, "The backup file is no longer available.")
        return redirect("backup_center")
    return FileResponse(path.open("rb"), as_attachment=True, filename=safe_filename)


@login_required
@require_POST
def restore_backup(request):
    uploaded = request.FILES.get("backup_file")
    if not uploaded:
        messages.error(request, "Choose a SQLite backup file first.")
        return redirect("backup_center")
    if uploaded.size > 100 * 1024 * 1024:
        messages.error(request, "The selected file exceeds the 100 MB limit.")
        return redirect("backup_center")

    temp_path = None
    try:
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in {".sqlite3", ".db", ".sqlite"}:
            raise ValidationError("Only .sqlite3, .sqlite, or .db backup files are accepted.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3") as temp:
            for chunk in uploaded.chunks():
                temp.write(chunk)
            temp_path = Path(temp.name)

        source = sqlite3.connect(str(temp_path))
        try:
            integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {row[0] for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if integrity != "ok" or "auth_user" not in tables or "django_migrations" not in tables:
                raise ValidationError("This file does not appear to be a valid backup of this Django project.")
        finally:
            source.close()

        target_path = _sqlite_path()
        # Close Django's active connection before replacing database contents.
        connections.close_all()

        source = sqlite3.connect(str(temp_path))
        target = sqlite3.connect(str(target_path), timeout=30)
        try:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            target.close()
            source.close()

        if integrity != "ok":
            raise ValidationError("Restored database failed its integrity check.")

        # Re-resolve user in the restored database to prevent Foreign Key constraint failure
        User = get_user_model()
        restored_user = User.objects.filter(pk=request.user.pk).first()

        safe_name = Path(uploaded.name).name[:255]
        BackupLog.objects.create(
            filename=safe_name, action="restored",
            file_size=uploaded.size, performed_by=restored_user
        )
        messages.success(request, "Database restored. Please sign in again if your session has ended.")
        logout(request)
        return redirect("login")
    except (OSError, sqlite3.Error, ValidationError, DatabaseError) as exc:
        messages.error(request, f"Restore failed: {exc}")
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
    return redirect("backup_center")

import io
import os
import sqlite3
import tempfile
from pathlib import Path

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import EntryForm
from .models import BackupLog, Entry

User = get_user_model()


class WorkspaceAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="StrongPass123!")
        self.other = User.objects.create_user(username="other", password="StrongPass123!")
        self.entry = Entry.objects.create(title="Private record", created_by=self.other)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_user_cannot_edit_another_users_entry(self):
        self.client.login(username="member", password="StrongPass123!")
        response = self.client.get(reverse("entry_edit", args=[self.entry.pk]))
        self.assertEqual(response.status_code, 404)

    def test_user_sees_only_own_entries(self):
        self.client.login(username="member", password="StrongPass123!")
        response = self.client.get(reverse("entry_list"))
        self.assertNotContains(response, "Private record")

    def test_dashboard_authenticated_context(self):
        self.client.login(username="member", password="StrongPass123!")
        Entry.objects.create(title="Member record", created_by=self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["entry_count"], 1)
        self.assertEqual(len(response.context["recent_entries"]), 1)


class EntryCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="author", password="StrongPass123!")
        self.other = User.objects.create_user(username="intruder", password="StrongPass123!")
        self.client.login(username="author", password="StrongPass123!")

    def test_entry_create_valid(self):
        response = self.client.post(reverse("entry_create"), {
            "title": "New Hackathon Idea",
            "category": "Innovation",
            "description": "Building something great."
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("entry_list"))
        entry = Entry.objects.get(title="New Hackathon Idea")
        self.assertEqual(entry.created_by, self.user)
        self.assertEqual(entry.category, "Innovation")

    def test_entry_create_invalid(self):
        response = self.client.post(reverse("entry_create"), {
            "title": "",
            "category": "Blank Title",
            "description": "Should fail validation."
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "title", "This field is required.")

    def test_entry_edit_own(self):
        entry = Entry.objects.create(title="Draft Title", created_by=self.user)
        response = self.client.post(reverse("entry_edit", args=[entry.pk]), {
            "title": "Final Title",
            "category": "Docs",
            "description": "Updated notes."
        })
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Final Title")
        self.assertEqual(entry.category, "Docs")

    def test_entry_delete_own_post(self):
        entry = Entry.objects.create(title="To be removed", created_by=self.user)
        response = self.client.post(reverse("entry_delete", args=[entry.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Entry.objects.filter(pk=entry.pk).exists())

    def test_entry_delete_get_not_allowed(self):
        entry = Entry.objects.create(title="Cannot GET delete", created_by=self.user)
        response = self.client.get(reverse("entry_delete", args=[entry.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Entry.objects.filter(pk=entry.pk).exists())

    def test_entry_delete_other_user_404(self):
        other_entry = Entry.objects.create(title="Other user entry", created_by=self.other)
        response = self.client.post(reverse("entry_delete", args=[other_entry.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Entry.objects.filter(pk=other_entry.pk).exists())


class AuthenticationWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="authuser", password="ValidPassword123!")

    def test_login_success(self):
        response = self.client.post(reverse("login"), {
            "username": "authuser",
            "password": "ValidPassword123!"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_invalid_password(self):
        response = self.client.post(reverse("login"), {
            "username": "authuser",
            "password": "WrongPassword!"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your username or password was incorrect.")

    def test_logout_post(self):
        self.client.login(username="authuser", password="ValidPassword123!")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        # Should redirect to login
        self.assertRedirects(response, reverse("login"))


class BackupUtilitiesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="backupadmin", password="ValidPassword123!")
        self.other = User.objects.create_user(username="otheradmin", password="ValidPassword123!")
        self.client.login(username="backupadmin", password="ValidPassword123!")

    def test_backup_endpoints_require_post(self):
        response = self.client.get(reverse("create_backup"))
        self.assertEqual(response.status_code, 405)
        response = self.client.get(reverse("restore_backup"))
        self.assertEqual(response.status_code, 405)

    def test_restore_rejects_missing_file(self):
        response = self.client.post(reverse("restore_backup"), {})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("backup_center"))

    def test_restore_rejects_invalid_extension(self):
        fake_file = SimpleUploadedFile("backup.txt", b"plain text content", content_type="text/plain")
        response = self.client.post(reverse("restore_backup"), {"backup_file": fake_file}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only .sqlite3, .sqlite, or .db backup files are accepted")

    def test_restore_rejects_corrupted_file(self):
        corrupt_file = SimpleUploadedFile("fake_db.sqlite3", b"this is not a sqlite database", content_type="application/x-sqlite3")
        response = self.client.post(reverse("restore_backup"), {"backup_file": corrupt_file}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Restore failed")

    def test_download_backup_isolation(self):
        # Create log owned by 'other'
        other_log = BackupLog.objects.create(
            filename="database-backup-sample.sqlite3",
            action="created",
            file_size=1024,
            performed_by=self.other
        )
        # backupadmin tries to download otheradmin's backup
        response = self.client.get(reverse("download_backup", args=[other_log.pk]))
        self.assertEqual(response.status_code, 404)

    def test_backup_and_download_flow(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "test_live.sqlite3"
            backups_dir = tmp_path / "backups"
            backups_dir.mkdir()

            # Create a valid sqlite database
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE auth_user (id INTEGER PRIMARY KEY, username TEXT);")
            conn.execute("CREATE TABLE django_migrations (id INTEGER PRIMARY KEY, app TEXT);")
            conn.commit()
            conn.close()

            with override_settings(
                DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": db_path}},
                BASE_DIR=tmp_path
            ):
                response = self.client.post(reverse("create_backup"), follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Backup created:")

                log = BackupLog.objects.filter(performed_by=self.user, action="created").first()
                self.assertIsNotNone(log)
                self.assertTrue((backups_dir / log.filename).exists())

                # Test download
                dl_response = self.client.get(reverse("download_backup", args=[log.pk]))
                self.assertEqual(dl_response.status_code, 200)
                self.assertEqual(dl_response.headers.get("Content-Disposition"), f'attachment; filename="{log.filename}"')
                dl_response.close()

                # Test valid restore
                with (backups_dir / log.filename).open("rb") as f:
                    restore_response = self.client.post(reverse("restore_backup"), {"backup_file": f}, follow=True)
                self.assertEqual(restore_response.status_code, 200)
                self.assertContains(response, "Backup created:")


class ModelAndAdminTests(TestCase):
    def test_model_str_representations(self):
        user = User.objects.create_user(username="modeltester", password="ValidPassword123!")
        entry = Entry.objects.create(title="My Model Item", created_by=user)
        self.assertEqual(str(entry), "My Model Item")

        log = BackupLog.objects.create(filename="backup-xyz.sqlite3", action="created", performed_by=user)
        self.assertEqual(str(log), "created: backup-xyz.sqlite3")

    def test_admin_registration(self):
        self.assertIn(Entry, site._registry)
        self.assertIn(BackupLog, site._registry)


class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notifier", password="StrongPass123!")

    def test_notify_new_entry_sends_email_on_create(self):
        from django.core import mail
        self.client.login(username="notifier", password="StrongPass123!")
        response = self.client.post(reverse("entry_create"), {
            "title": "Incident #404",
            "category": "Operations",
            "description": "Urgent review required."
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("[Foundry Alert] New record created: Incident #404", sent.subject)
        self.assertIn("habervincent21@gmail.com", sent.to)
        self.assertIn("Incident #404", sent.body)
        self.assertIn("http://127.0.0.1:8000/entries/", sent.body)

    def test_send_admin_alert_without_recipients(self):
        from .notifications import send_admin_alert
        with override_settings(ADMIN_EMAIL=""):
            result = send_admin_alert("Test Subject", "Test Body")
            self.assertFalse(result)

    def test_send_admin_alert_handles_exception_safely(self):
        from unittest.mock import patch
        from .notifications import send_admin_alert
        with patch("django.core.mail.EmailMultiAlternatives.send", side_effect=Exception("SMTP simulated error")):
            result = send_admin_alert("Test", "Body")
            self.assertFalse(result)

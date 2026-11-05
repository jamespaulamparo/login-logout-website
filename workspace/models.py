from django.conf import settings
from django.db import models

class Entry(models.Model):
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspace_entries")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

class BackupLog(models.Model):
    ACTIONS = [("created", "Created"), ("restored", "Restored")]
    filename = models.CharField(max_length=255)
    action = models.CharField(max_length=20, choices=ACTIONS)
    file_size = models.PositiveBigIntegerField(default=0)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}: {self.filename}"

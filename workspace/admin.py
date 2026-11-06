from django.contrib import admin
from .models import BackupLog, EmailVerificationOTP, Entry

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_by", "updated_at")
    search_fields = ("title", "category", "description")

@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ("filename", "action", "file_size", "performed_by", "created_at")
    readonly_fields = ("filename", "action", "file_size", "performed_by", "created_at")

@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "otp_code", "attempts", "is_used", "created_at", "expires_at")
    search_fields = ("email", "otp_code")
    readonly_fields = ("email", "otp_code", "attempts", "is_used", "created_at", "expires_at")

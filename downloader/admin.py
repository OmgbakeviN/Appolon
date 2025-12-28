from django.contrib import admin
from .models import DownloadEvent


@admin.register(DownloadEvent)
class DownloadEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "user", "mode", "title", "video_id", "quality_label", "ip_address", "browser", "os", "device"
    )
    list_filter = ("mode", "created_at", "browser", "os")
    search_fields = ("title", "video_id", "video_url", "ip_address", "browser", "os", "device", "quality_label")
    readonly_fields = ("created_at",)

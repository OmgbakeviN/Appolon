from django.conf import settings
from django.db import models


class DownloadEvent(models.Model):
    MODE_CHOICES = (
        ("audio", "Audio"),
        ("video", "Video"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="download_events",
    )

    video_url = models.URLField()
    video_id = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=255, blank=True)

    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    format_id = models.CharField(max_length=32, blank=True)
    ext = models.CharField(max_length=10, blank=True)
    quality_label = models.CharField(max_length=80, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    browser = models.CharField(max_length=80, blank=True)
    os = models.CharField(max_length=80, blank=True)
    device = models.CharField(max_length=80, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.mode} - {self.title or self.video_id} ({self.created_at:%Y-%m-%d %H:%M})"

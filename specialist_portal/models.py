# links/models.py
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class LinkRequest(models.Model):
    """
    طلب ربط طفل بأخصائي. ينشئه وليّ الأمر (أو النظام)
    ويوافق/يرفضه الأخصائي.
    """
    STATUS = (
        ("pending", "قيد المراجعة"),
        ("approved", "مقبول"),
        ("rejected", "مرفوض"),
        ("expired",  "منتهي"),
    )
    child = models.ForeignKey(User, on_delete=models.CASCADE, related_name="specialist_link_requests")
    specialist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="incoming_link_requests")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_link_requests")

    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("child", "specialist")  # لا نكرر نفس الطلب لنفس الثنائي
        ordering = ["-created_at"]

    def __str__(self):
        return f"Link {self.child} -> {self.specialist} [{self.status}]"

# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('child', 'طفل'),
        ('parent', 'ولي أمر'),
        ('specialist', 'أخصائي'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPES)

    # ⬇️ لكل طفل: وليّ أمر واحد وأخصائي واحد (One-to-Many)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="children",
        limit_choices_to={'user_type': 'parent'},
        help_text="ولي الأمر لهذا الطفل (اختياري مؤقتًا)"
    )
    specialist = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="patients",
        limit_choices_to={'user_type': 'specialist'},
        help_text="الأخصائي لهذا الطفل (اختياري مؤقتًا)"
    )

    def clean(self):
        # تأكد إن القيَم منطقية حسب النوع
        if self.user_type == 'child':
            if self.parent and self.parent.user_type != 'parent':
                raise ValidationError("الحقل parent يجب أن يكون مستخدمًا من نوع 'ولي أمر'.")
            if self.specialist and self.specialist.user_type != 'specialist':
                raise ValidationError("الحقل specialist يجب أن يكون مستخدمًا من نوع 'أخصائي'.")
        else:
            # لو المستخدم Parent/Specialist، ماينفعش يتعيّن له parent/specialist
            if self.parent_id:
                raise ValidationError("لا يمكن تعيين وليّ أمر لمستخدم ليس طفلًا.")
            if self.specialist_id:
                raise ValidationError("لا يمكن تعيين أخصائي لمستخدم ليس طفلًا.")

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

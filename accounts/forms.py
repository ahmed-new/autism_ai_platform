# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPES, label="نوع المستخدم")
    age_years = forms.IntegerField(
        required=False,
        label="العمر (بالسنوات)",
        min_value=4,
        max_value=8,  # عدّل المدى كما يلزمك
        help_text="أدخل العمر بالسنوات."
    )

    parent = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        label="وليّ الأمر",
        empty_label="اختر وليّ أمر…"
    )
    specialist = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        label="الأخصائي",
        empty_label="اختر أخصائي…"
    )

    class Meta:
        model = CustomUser
        fields = ("username","age_years", "email", "user_type", "parent", "specialist", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Querysets طبيعية
        self.fields["parent"].queryset = CustomUser.objects.filter(
            user_type="parent", is_active=True
        ).order_by("username")

        self.fields["specialist"].queryset = CustomUser.objects.filter(
            user_type="specialist", is_active=True
        ).order_by("username")

        # نحدد هل نظهر صفوف الطفل بالواجهة
        if self.data:
            utype = self.data.get("user_type")
            
        else:
            utype = self.initial.get("user_type") if self.initial else None
        self.show_child_fields = (utype == "child")

        # مهم: لا تغيّر الـ widget إلى HiddenInput
        # فقط تأكد إنهم غير إجباريين مبدئيًا
        self.fields["parent"].required = False
        self.fields["specialist"].required = False
        self.fields["age_years"].required = self.show_child_fields
        # لو حابب تجعل وليّ الأمر إجباريًا عند الطفل:
        # if self.show_child_fields:
        #     self.fields["parent"].required = True

    def clean(self):
        cleaned = super().clean()
        utype = cleaned.get("user_type")
        parent = cleaned.get("parent")
        specialist = cleaned.get("specialist")
        age= cleaned.get("age")

        if utype == "child":
            if parent and parent.user_type != "parent":
                self.add_error("parent", "المحدد ليس وليّ أمر.")
            if specialist and specialist.user_type != "specialist":
                self.add_error("specialist", "المحدد ليس أخصائيًا.")
            if age is None:
                self.add_error("age_years", "العمر مطلوب عند تسجيل طفل.")
        else:
            # تجاهل أي قيم لو النوع مش طفل
            cleaned["parent"] = None
            cleaned["specialist"] = None
            cleaned["age_years"] = None

        return cleaned

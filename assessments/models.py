from django.db import models
from django.conf import settings




# المهارات الرئيسية
class SkillCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name



# الجروب داخل المهارة الرئيسية
class SkillGroup(models.Model):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.category.name} - {self.name}"




# المهارة الفرعية
class Skill(models.Model):
    group = models.ForeignKey(SkillGroup, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name




# السؤال نفسه
class Question(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()

    QUESTION_TYPES = [
        ('text_choice', 'اختيارات نصية'),
        ('image_choice', 'اختيارات صور'),
        ('drag_and_drop', 'سحب وإفلات'),
        ('audio_input', 'إدخال صوتي'),
    ]
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)

    image = models.ImageField(upload_to='questions/images/', blank=True, null=True)

    video = models.FileField(upload_to='videos/', blank=True, null=True)
 

    options = models.JSONField(help_text="قائمة الاختيارات، يمكن أن تكون نصوصًا أو روابط صور")

    DIFFICULTY_LEVELS = [
        (1, 'سهل'),
        (2, 'متوسط'),
        (3, 'صعب'),
    ]
    difficulty = models.IntegerField(choices=DIFFICULTY_LEVELS, default=1)

    correct_answer = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"سؤال: {self.question_text[:30]}..."




from django.utils import timezone

class AssessmentSession(models.Model):
    STATUS_CHOICES = (
        ("active", "نشطة"),
        ("completed", "مكتملة"),
        ("aborted", "تم إنهاؤها"),
    )
    child = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_sessions")
    category = models.ForeignKey(SkillCategory, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    total_questions = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)

    # سنخزن لقطة لحالة السيشن (اختياري للمراجعة السريعة)
    state_snapshot = models.JSONField(null=True, blank=True)

    @property
    def duration_timedelta(self):
        start = self.started_at or timezone.now()
        end = self.ended_at or timezone.now()
        return max(end - start, timezone.timedelta(0))

    @property
    def duration_seconds(self) -> int:
        return int(self.duration_timedelta.total_seconds())

    @property
    def duration_human(self) -> str:
        secs = self.duration_seconds
        h, r = divmod(secs, 3600)
        m, s = divmod(r, 60)
        if h: return f"{h}س {m}د {s}ث"
        if m: return f"{m}د {s}ث"
        return f"{s}ث"

    def __str__(self):
        return f"Session #{self.id} - {self.child} - {self.get_status_display()}"
    

# تتبع أداء الطفل على الأسئلة
class QuestionAnswer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    session = models.ForeignKey(AssessmentSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="answers")
    def __str__(self):
        return f"{self.user} - {self.question} - {'✔️' if self.is_correct else '❌'}"







class EyeGazeSample(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey('AssessmentSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='gaze_samples')
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True)
    t = models.DateTimeField()  # وقت العينة
    x = models.IntegerField()
    y = models.IntegerField()
    on_task = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'session']),
            models.Index(fields=['question']),
        ]

class EyeGazeSummary(models.Model):
    """ملخص لكل سؤال داخل الجلسة (اختياري للتقارير السريعة)."""
    session = models.ForeignKey('AssessmentSession', on_delete=models.CASCADE, related_name='gaze_summaries')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    samples = models.PositiveIntegerField(default=0)
    on_task_samples = models.PositiveIntegerField(default=0)
    attention_pct = models.FloatField(default=0.0)  # 0..100 آخر تحديث

    class Meta:
        unique_together = ('session', 'question')








# assessments/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class ParentSCQSubmission(models.Model):
    """
    استبيان وليّ الأمر (SCQ) - نسخة عربية مبسّطة
    - استبيان ثابت: نخزّن الأسئلة/الإجابات في JSON
    - ممكن نربطه بجلسة تقويم (AssessmentSession) أو يفضل مستقل
    """
    child = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scq_submissions")
    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="given_scq")
    session = models.ForeignKey('assessments.AssessmentSession', on_delete=models.SET_NULL, null=True, blank=True)

    # بيانات أولية يدخلها ولي الأمر:
    parent_full_name = models.CharField(max_length=255, blank=True)
    child_age_years = models.PositiveIntegerField(null=True, blank=True)
    child_sex = models.CharField(max_length=10, blank=True)  # "ذكر" / "أنثى"
    residence = models.CharField(max_length=255, blank=True)
    child_diagnosis = models.CharField(max_length=255, blank=True)

    # الإجابات: خريطة {رقم_السؤال: "نعم"/"لا"}
    answers = models.JSONField(default=dict, blank=True)

    # تلخيص بسيط (اختياري): إجمالي نعم/لا
    yes_count = models.PositiveIntegerField(default=0)
    no_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SCQ for {self.child} on {self.created_at.date()}"

    def recompute_counts(self):
        a = self.answers or {}
        ys = sum(1 for v in a.values() if str(v).strip() == "نعم")
        ns = sum(1 for v in a.values() if str(v).strip() == "لا")
        self.yes_count = ys
        self.no_count = ns

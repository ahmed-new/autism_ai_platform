from django.contrib import admin
from .models import SkillCategory, Skill , SkillGroup ,Question , QuestionAnswer   , AssessmentSession

admin.site.register(SkillCategory)
admin.site.register(Skill)
admin.site.register(SkillGroup)
# admin.site.register(Question)
admin.site.register(QuestionAnswer)
admin.site.register(AssessmentSession)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'skill', 'question_type', 'difficulty']
    list_filter = ['skill', 'question_type', 'difficulty']
    search_fields = ['question_text']

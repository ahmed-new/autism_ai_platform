from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from assessments.models import SkillCategory 
import json
from django.utils import timezone
from assessments.models import AssessmentSession







User = get_user_model()


@login_required
def child_home(request):
    if request.user.user_type != 'child':
        return render(request, "unauthorized.html")

    categories = SkillCategory.objects.all()
    return render(request, "child_interface/home.html", {
        "child": request.user,
        "categories": categories
    })








@csrf_exempt
@login_required
def start_ai_session(request):
    if request.user.user_type != "child":
        return render(request, "unauthorized.html")

    if request.method == "POST":
        from assessments.models import SkillCategory, SkillGroup

        category_id = request.POST.get("category_id")
        try:
            category = SkillCategory.objects.get(id=category_id)
        except SkillCategory.DoesNotExist:
            return HttpResponse("التصنيف غير موجود", status=404)

        groups = SkillGroup.objects.filter(category=category).prefetch_related("skills")
        skills = [skill for group in groups for skill in group.skills.all()]
        skill_names = [s.name for s in skills]


        # قبل إنشاء الجلسة الجديدة مباشرة
        prev = request.session.get("ai_session")
        if prev and prev.get("db_session_id"):
            AssessmentSession.objects.filter(
                id=prev["db_session_id"], child=request.user, status="active"
            ).update(status="aborted", ended_at=timezone.now())

        # نظّف حاله السيشن القديمة – مش ضروري، بس أأمن
        request.session.pop("ai_session", None)

        # ✨ NEW: أنشئ سجل جلسة فعلي في الداتا بيز
        db_session = AssessmentSession.objects.create(
            child=request.user,
            status="active",
            started_at=timezone.now(),
            total_questions=0,
            correct_count=0,
            wrong_count=0,
            state_snapshot={},
        )

        request.session["ai_session"] = {
            "category_id": category.id,
            "skill_ids": [s.id for s in skills],
            "current_skill_index": 0,
            "current_difficulty": 1,
            "wrong_attempts": 0,
            "skills_status": [],
            "db_session_id": db_session.id,  # ✨ مهم جدًا
        }
        request.session.modified = True

        return render(request, "child_interface/ai_session.html", {
            "child": request.user,
            "category": category,
            "skills": json.dumps(skill_names, ensure_ascii=False),
        })

    return HttpResponse("ممنوع الوصول المباشر.")

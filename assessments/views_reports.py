# assessments/views_reports.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required

from accounts.models import CustomUser
from .models import AssessmentSession, Skill
from .analytics import (
    compute_child_groups_overview,  # سنستخدمه للأوفر فيو لكن نمرره كمفتاح "skills"
    compute_skill_detail, 
    compute_child_skills_overview,  
    compute_child_session_trend,        # يُرجع question_text في أضعف الأسئلة
)

# ===== صلاحيات الوصول =====
def _can_view_child(viewer, child):
    """يسمح لوليّ الأمر أو الأخصائي المرتبط أو الأدمن فقط بعرض تقرير الطفل."""
    if viewer.is_superuser or viewer.is_staff:
        return True
    if viewer.user_type == "parent" and child.parent_id == viewer.id:
        return True
    if viewer.user_type == "specialist" and child.specialist_id == viewer.id:
        return True
    return False


# ====== نظرة عامة لكل مهارات الطفل (HTML) ======
@login_required
def child_skills_overview_view(request, child_id):
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return HttpResponseForbidden("غير مصرح بعرض هذا التقرير.")

    session_id = request.GET.get("session_id")
    session = None
    if session_id and session_id != "all":
        session = AssessmentSession.objects.filter(id=session_id, child=child).first()
    elif session_id == "all":
        session = None
    else:
        # 👇 الافتراضي: آخر جلسة للطفل (عشان ميبقاش تجميعي)
        session = AssessmentSession.objects.filter(child=child).order_by("-started_at", "-id").first()

    # دالة الجروبات اللي كتبناها سابقًا
    groups = compute_child_groups_overview(child, session=session)
    session_trend = compute_child_session_trend(child)

    context = {"child": child, "skills": groups, "session": session,"session_trend": session_trend}
    return render(request, "reports/child_skills_overview.html", context)


# ====== تقرير مهارة واحدة (HTML) ======
@login_required
def skill_detail_view(request, child_id, skill_id):
    """
    صفحة HTML تعرض تفاصيل مهارة واحدة:
      - الدقة الموزونة
      - انتباه WebGazer
      - توزيع الأداء حسب الصعوبة
      - أضعف الأسئلة داخل المهارة (تظهر نص السؤال)
    اختيارياً: ?session_id=123 لتصفية على جلسة معينة.
    """
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return HttpResponseForbidden("غير مصرح بعرض هذا التقرير.")

    # تأكد أن المهارة موجودة (هنعرض اسمها في القالب)
    skill = get_object_or_404(Skill, id=skill_id)

    session_id = request.GET.get("session_id")
    session = (
        AssessmentSession.objects.filter(id=session_id, child=child).first()
        if session_id else None
    )

    detail = compute_skill_detail(child, skill_id, session=session)

    context = {
        "child": child,
        "skill": skill,
        "detail": detail,   # {accuracy_pct, attention_pct, level, distribution_by_difficulty, weakest_questions(question_text), ...}
        "session": session,
    }
    return render(request, "reports/skill_detail.html", context)


# ====== نظرة عامة (JSON API) ======
@login_required
def child_skills_overview_api(request, child_id):
    """
    واجهة JSON لعرض نظرة عامة لكل مجموعات المهارات.
    اختيارياً: ?session_id=123
    (نحافظ على المفتاح "skills" للتوافق مع الواجهة الحالية)
    """
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return JsonResponse({"error": "forbidden"}, status=403)

    session_id = request.GET.get("session_id")
    session = (
        AssessmentSession.objects.filter(id=session_id, child=child).first()
        if session_id else None
    )

    data = compute_child_groups_overview(child, session=session)
    return JsonResponse(
        {
            "child": child.username,
            "session_id": getattr(session, "id", None),
            "skills": data,  # ← مجموعة المجموعات تُعاد في المفتاح "skills"
        },
        json_dumps_params={"ensure_ascii": False},
    )


# ====== تقرير مهارة واحدة (JSON API) ======
@login_required
def skill_detail_api(request, child_id, skill_id):
    """
    واجهة JSON لتقرير مهارة واحدة.
    اختيارياً: ?session_id=123
    (weakest_questions تحتوي question_text بدل question_id)
    """
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return JsonResponse({"error": "forbidden"}, status=403)

    # تأكيد وجود المهارة
    get_object_or_404(Skill, id=skill_id)

    session_id = request.GET.get("session_id")
    session = (
        AssessmentSession.objects.filter(id=session_id, child=child).first()
        if session_id else None
    )

    detail = compute_skill_detail(child, skill_id, session=session)
    return JsonResponse(detail, json_dumps_params={"ensure_ascii": False})





# أعلى الملف: أضف الاستيراد التالي مع البقية
from .models import AssessmentSession, Skill, SkillGroup  # ← SkillGroup مضافة هنا

# ... بقية الكود كما هو ...

# ====== قائمة مهارات مجموعة واحدة (HTML) ======
@login_required
def group_skills_view(request, child_id, group_id):
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return HttpResponseForbidden("غير مصرح بعرض هذا التقرير.")

    group = get_object_or_404(SkillGroup, id=group_id)

    session_id = request.GET.get("session_id")
    session = None
    if session_id and session_id != "all":
        session = AssessmentSession.objects.filter(id=session_id, child=child).first()
    elif session_id == "all":
        session = None
    else:
        session = AssessmentSession.objects.filter(child=child).order_by("-started_at", "-id").first()

    all_skills = compute_child_skills_overview(child, session=session)
    group_skill_ids = set(Skill.objects.filter(group_id=group.id).values_list("id", flat=True))
    skills = [s for s in all_skills if s["skill_id"] in group_skill_ids]

    return render(request, "reports/group_skills.html", {
        "child": child, "group": group, "skills": skills, "session": session,
    })


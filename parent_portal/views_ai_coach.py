# assessments/views_parent_ai.py
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from accounts.models import CustomUser
from assessments.models import (
    AssessmentSession, Skill, QuestionAnswer, ParentSCQSubmission
)

from assessments.analytics import (
    compute_child_groups_overview,
    compute_skill_detail,
)

# === صلاحيات عامة ===
def _can_view_child(viewer, child):
    if viewer.is_superuser or viewer.is_staff:
        return True
    if viewer.user_type == "parent" and child.parent_id == viewer.id:
        return True
    if viewer.user_type == "specialist" and child.specialist_id == viewer.id:
        return True
    return False


# ---------- مساعد الذكاء ----------
def _pick_session(child, session_id):
    """اختر جلسة: بالـid لو موجود، وإلا آخر جلسة مكتملة، وإلا آخر جلسة أيًا كانت، وإلا None."""
    if session_id:
        s = AssessmentSession.objects.filter(id=session_id, child=child).first()
        if s:
            return s
    s = (AssessmentSession.objects
         .filter(child=child, status="completed")
         .order_by("-started_at", "-id").first())
    if s:
        return s

    return (AssessmentSession.objects
            .filter(child=child)
            .order_by("-started_at", "-id").first())


def _session_tested_skills(child, session):
    """
    رجّع المهارات التي ظهر لها أسئلة مُجابة في الجلسة المحددة.
    fallback: لو مفيش جلسة/إجابات، رجّع كل مهارات الطفل تاريخيًا.
    """
    qs = Skill.objects.none()
    if session:
        qs = (Skill.objects
              .filter(questions__questionanswer__user=child,
                      questions__questionanswer__session=session)
              .distinct())
    if not qs.exists():
        qs = (Skill.objects
              .filter(questions__questionanswer__user=child)
              .distinct())
    return qs.order_by("name")


def _latest_scq(child):
    return (ParentSCQSubmission.objects
            .filter(child=child)
            .order_by("-created_at").first())


def _build_scq_summary(scq: ParentSCQSubmission | None) -> dict:
    """
    ملخص صغير لاستبيان SCQ لإدخاله في الـ prompt.
    نضيف العدادات والقائمة الكاملة للإجابات (نعم/لا) لو موجودة.
    """
    if not scq:
        return {
            "available": False,
            "note": "لا توجد استبانة SCQ محفوظة.",
        }
    return {
        "available": True,
        "created_at": scq.created_at.strftime("%Y-%m-%d %H:%M"),
        "yes_count": scq.yes_count or 0,
        "no_count": scq.no_count or 0,
        "answers": scq.answers or {},
    }


def _build_ai_payload(child, session, group_overview, focus_skill_ids):
    """
    نبني حزمة بيانات مركّزة تُرسل للنموذج: نظرة عامة بالمجموعات،
    وتفاصيل للمهارات المختارة، مع ملخص آخر SCQ.
    """
    # تفاصيل المهارات المختارة (إن وُجدت)
    skills_detail = []
    for sid in (focus_skill_ids or []):
        try:
            d = compute_skill_detail(child, sid, session=session)
            # نخفّض حجم الـpayload (خلي الأسئلة الأضعف 3 فقط)
            if d.get("weakest_questions"):
                d["weakest_questions"] = d["weakest_questions"][:3]
            skills_detail.append(d)
        except Exception:
            # تجاهل أية مهارة حصل فيها خطأ
            continue

    scq = _latest_scq(child)
    scq_summary = _build_scq_summary(scq)

    payload = {
        "child": {
            "name": child.username,
            "age_years": getattr(child, "age_years", None),
        },
        "session": ({
            "id": session.id,
            "status": session.status,
            "started_at": session.started_at.strftime("%Y-%m-%d %H:%M") if session.started_at else None,
            "ended_at": session.ended_at.strftime("%Y-%m-%d %H:%M") if session.ended_at else None,
        } if session else None),
        "overview_by_group": group_overview,   # ناتج compute_child_groups_overview
        "focus_skills_detail": skills_detail,  # من compute_skill_detail
        "scq": scq_summary,                    # ملخص آخر استبيان
        "timestamp": timezone.now().isoformat(),
    }
    return payload


def _compose_system_prompt():
    return (
        "أنت مساعد متخصص في تدريب أولياء الأمور على دعم أطفالهم ذوي اضطراب طيف التوحُّد.\n"
        "ستتلقى بيانات تقرير جلسة تقييم + آخر استبيان SCQ. قدّم خطة عملية منزلية مبنية على البيانات.\n"
        "المطلوب دائمًا:\n"
        "1) فقرة قصيرة ترحّب بوليّ الأمر وتلخّص أهم نقاط القوة والضعف.\n"
        "2) 3–5 أهداف سلوكية/تعليمية قصيرة المدى (SMART) مرتبطة بالمهارات الأضعف.\n"
        "3) أنشطة يومية بسيطة (10–15 دقيقة) مع خطوات تنفيذ دقيقة، وأمثلة لعب/لغة، وتدريج صعوبة.\n"
        "4) استراتيجيات تواصل وإدارة سلوك (تعزيز، تهيئة بيئة، تلميحات، نمذجة، خيارات محدودة).\n"
        "5) مؤشرات متابعة منزلية أسبوعية وكيف يعرف وليّ الأمر أن الطفل يتقدّم.\n"
        "6) لو كان في استبيان SCQ، استخدمه لتعديل الخطة (بدون تشخيص طبي). \n"
        "اللغة: عربية مبسطة وداعمة، بدون أحكام، وبدون أي ادّعاء تشخيصي. لا تختصر الردّ."
    )


def _compose_user_prompt(custom_message: str | None):
    return custom_message.strip() if custom_message else (
        "حلّل التقرير وقدّم خطة منزلية واضحة تركّز على أضعف المهارات."
    )


def _sanitize_for_safety(text: str) -> str:
    if not text:
        return text
    replace_map = {
        "يضرب": "[سلوك عالي الخطورة]",
        "ضرب": "[سلوك عالي الخطورة]",
        "يؤذي": "[سلوك عالي الخطورة]",
        "إيذاء": "[سلوك عالي الخطورة]",
        "خبط الرأس": "[سلوك عالي الخطورة]",
        "عض": "[سلوك عالي الخطورة]",
        "قتل": "[سلوك عالي الخطورة]",
        "انتحار": "[سلوك عالي الخطورة]",
    }
    for k, v in replace_map.items():
        text = text.replace(k, v)
    return text


def _safety_settings():
    """
    تُعيد إعدادات السلامة بطريقة متوافقة مع أكثر من إصدار:
    - لو enums متاحة: نستخدمها.
    - لو مش متاحة: نستخدم السلاسل النصية.
    - من غير SELF_HARM لو غير مدعومة في الإصدار الحالي.
    """
    try:
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        safety = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HARASSMENT:       HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH:      HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
        # بعض الإصدارات عندها SEXUAL_AND_MINORS، وبعضها SEXUAL_CONTENT
        if hasattr(HarmCategory, "HARM_CATEGORY_SEXUAL_AND_MINORS"):
            safety[HarmCategory.HARM_CATEGORY_SEXUAL_AND_MINORS] = HarmBlockThreshold.BLOCK_ONLY_HIGH
        elif hasattr(HarmCategory, "HARM_CATEGORY_SEXUAL_CONTENT"):
            safety[HarmCategory.HARM_CATEGORY_SEXUAL_CONTENT] = HarmBlockThreshold.BLOCK_ONLY_HIGH

        # SELF_HARM غير موجودة في بعض الإصدارات
        if hasattr(HarmCategory, "HARM_CATEGORY_SELF_HARM"):
            safety[HarmCategory.HARM_CATEGORY_SELF_HARM] = HarmBlockThreshold.BLOCK_ONLY_HIGH

        return safety
    except Exception:
        # fallback بالإسم النصي (مدعوم في نسخ قديمة/مختلفة)
        safety = [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUAL_AND_MINORS", "threshold": "BLOCK_ONLY_HIGH"},
            # لو مكتبتك ما بتعرفش SELF_HARM سيبه متشال
            # {"category": "HARM_CATEGORY_SELF_HARM",         "threshold": "BLOCK_ONLY_HIGH"},
        ]
        return safety


def _call_gemini(payload: dict, user_prompt: str):
    """
    اتصال مبسّط مع Gemini مع إعدادات سلامة متوافقة مع الإصدارات المختلفة.
    يعقّم النص لتقليل حجب dangerous_content ويعطي fallback ودّي عند 429/أخطاء.
    """
    import json
    from django.conf import settings

    try:
        import google.generativeai as genai
    except Exception as e:
        return (
            "تعذّر الاتصال بالمساعد الذكي الآن (المكتبة غير مثبّتة).\n\n"
            "ثبّت الحزمة:\n"
            "    pip install google-generativeai\n\n"
            f"(تفاصيل: {e})"
        )

    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return (
            "تعذّر الاتصال بالمساعد الذكي الآن (GEMINI_API_KEY غير مُعرّف).\n"
            "أضِف المفتاح في الإعدادات أو متغيرات البيئة."
        )

    try:
        genai.configure(api_key=api_key)

        safety = _safety_settings()

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=_compose_system_prompt(),
            safety_settings=safety,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 3072,
                # النسخة عندك لا تقبل text/markdown — استخدم text/plain أو احذف السطر
                "response_mime_type": "text/plain",
            },
        )

        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        payload_json = _sanitize_for_safety(payload_json)
        user_prompt  = _sanitize_for_safety(_compose_user_prompt(user_prompt))

        resp = model.generate_content(
            [
                {"role": "user", "parts": [payload_json]},
                {"role": "user", "parts": [user_prompt]},
            ]
        )

        fb = getattr(resp, "prompt_feedback", None)
        if fb and getattr(fb, "block_reason", None):
            return (
                "تم حجب جزء من الرد بسبب فلاتر السلامة.\n"
                "إرشادات عامة آمنة:\n"
                "• أنشطة منزلية بسيطة 10–15 دقيقة لهدف واحد.\n"
                "• لغة بسيطة، اختيارين فقط، وتعزيز إيجابي فوري.\n"
                "• في حال [سلوك عالي الخطورة] تواصل مع مختص/جهة مساعدة.\n"
            )

        text = (resp.text or "").strip()
        if not text:
            raise RuntimeError("ردّ فارغ من الموديل.")
        return text

    except Exception as e:
        s = str(e).lower()
        if "quota" in s or "429" in s or "exceed" in s:
            return (
                "تعذّر الاتصال بالمساعد الذكي الآن (تجاوزت الحصّة/الحد المسموح).\n"
                "جرّب لاحقًا أو راجع إعدادات الفوترة في Google AI Studio."
            )

        return (
            "تعذّر الاتصال بالمساعد الذكي الآن.\n\n"
            "خطة بديلة سريعة:\n"
            "• اختر هدفًا بسيطًا يرتبط بأضعف مهارة (مثال: طلب شيء بكلمتين).\n"
            "• 10 دقائق يوميًا: نموذج → تلميح → تعزيز فوري.\n"
            "• قلّل المشتتات وكرّر محاولات قصيرة وارفَع الصعوبة تدريجيًا.\n"
            "• راجع التقدّم أسبوعيًا وحدّد خطوة تالية.\n\n"
            f"(تفاصيل الخطأ: {e})"
        )







@login_required
def parent_ai_coach(request, child_id):
    """
    صفحة المساعد الذكي لوليّ الأمر.
    - تبني قائمة التركيز من المهارات التي ظهرت في الجلسة المختارة.
    - تُمرّر ملخص آخر SCQ داخل الـprompt.
    - تتيح زر 'متابعة الرد' لاستكمال نص طويل.
    """
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return HttpResponseForbidden("غير مصرح.")

    # اختر الجلسة (من GET ?session_id=)
    session_id = request.GET.get("session_id")
    session = _pick_session(child, session_id)

    # نظرة عامة بالمجموعات (Session-aware)
    groups = compute_child_groups_overview(child, session=session)

    # مهارات هذه الجلسة تلقائيًا
    focus_qs = _session_tested_skills(child, session)
    focus_skills = list(focus_qs.values("id", "name"))

    ai_answer = None
    last_payload = None

    if request.method == "POST":
        # المهارات المختارة يدويًا (checkboxes)
        selected = request.POST.getlist("focus[]")
        try:
            selected_ids = [int(s) for s in selected if str(s).isdigit()]
        except Exception:
            selected_ids = []

        # لو محددش حاجة، نختار أول 2 تلقائيًا (إن وُجدوا)
        if not selected_ids and focus_skills:
            selected_ids = [focus_skills[0]["id"]]
            if len(focus_skills) > 1:
                selected_ids.append(focus_skills[1]["id"])

        user_msg = request.POST.get("message", "").strip()
        if "continue" in request.POST:
            # زر متابعة: رسالة قصيرة تطلب الإكمال
            user_msg = (user_msg + "\n\nأكمل الرد السابق بالتفصيل.") if user_msg else "أكمل الرد السابق بالتفصيل."

        # ابني الـpayload وأرسله للموديل
        last_payload = _build_ai_payload(
            child=child,
            session=session,
            group_overview=groups,
            focus_skill_ids=selected_ids,
        )
        ai_answer = _call_gemini(last_payload, user_msg or "حلّل وقدّم خطة منزلية مفصلة.")

    context = {
        "child": child,
        "session": session,
        "groups": groups,
        "focus_skills": focus_skills,   # [{id, name}, ...] مهارات الجلسة
        "ai_answer": ai_answer,
    }
    return render(request, "parent_portal/ai_coach.html", context)

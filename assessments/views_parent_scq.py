# assessments/views_parent_scq.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from accounts.models import CustomUser
from .models import ParentSCQSubmission, AssessmentSession

# نفس منطق السماح بالعرض/التعديل للأطفال المرتبطين بالولي
def _can_view_child(viewer, child):
    if viewer.is_superuser or viewer.is_staff:
        return True
    if viewer.user_type == "parent" and child.parent_id == viewer.id:
        return True
    if viewer.user_type == "specialist" and child.specialist_id == viewer.id:
        return True
    return False

# === الأسئلة (نسخة عربية مبسطة وفق ما أرسلته) ===
SCQ_AR_ITEMS = [
    # تعليمات: إذا كانت إجابة (1) = لا، نتخطى 2→7
    {"num": 1, "text": "هل يستطيع طفلك الآن التحدث (عبارات قصيرة أو جمل)؟"},
    {"num": 2, "text": "هل يمكنك إجراء “محادثة” ذهابًا وإيابًا معه/معها (تناوب والاعتماد على ما قلتَه)؟"},
    {"num": 3, "text": "هل استخدم (أو يستخدم) عبارات غريبة أو يكرر نفس الشيء بنفس الطريقة مرارًا؟"},
    {"num": 4, "text": "هل استخدم أسئلة/تصريحات غير مناسبة اجتماعيًا (مثل أسئلة/تعليقات شخصية في أوقات غير مناسبة)؟"},
    {"num": 5, "text": "هل خلط الضمائر (مثل قول: هو/هي بدلًا من أنا/أنت)؟"},
    {"num": 6, "text": "هل استخدم كلمات مخترعة أو تعابير مجازية غريبة للتعبير (مثل قول: “المطر الساخن” بدل البخار)؟"},
    {"num": 7, "text": "هل كرر نفس القول مرارًا بنفس الطريقة أو أصر أن تكرر أنت الشيء نفسه؟"},

    {"num": 8, "text": "هل لديه/لديها أشياء يجب أن تُفعل بطريقة أو ترتيب معيّن أو طقوس يُصرّ على اتباعها؟"},
    {"num": 9, "text": "هل بدت تعابير وجهه/وجهها عادةً مناسبة للموقف قدر علمك؟"},
    {"num": 10, "text": "هل استخدم يدك كأداة/جزء من جسمه (مثل تحريك يدك لفتح الباب أو الإشارة بإصبعك)؟"},
    {"num": 11, "text": "هل لديه اهتمامات تشغله تبدو غريبة للآخرين (مثل إشارات المرور، المزاريب، الرسوم المتحركة)؟"},
    {"num": 12, "text": "هل اهتم بأجزاء من لعبة/شيء (كإدارة عجلات سيارة) أكثر من استخدامه كما هو مُصمَّم؟"},
    {"num": 13, "text": "هل كانت لديه اهتمامات خاصة غير عادية في شدتها لكنها مناسبة لعمره (مثل القطارات/الديناصورات)؟"},
    {"num": 14, "text": "هل بدا مهتمًا بشكل خاص بالرؤية/اللمس/الصوت/الطعم/الشم للأشياء أو الأشخاص؟"},
    {"num": 15, "text": "هل كانت لديه حركات غير عادية لليدين/الأصابع (رفرفة، تحريك الأصابع أمام العينين)؟"},
    {"num": 16, "text": "هل قام بحركات متكررة معقّدة للجسم (الدوران حول نفسه، انثناء متكرر للجسم)؟"},
    {"num": 17, "text": "هل آذى نفسه عمدًا (مثل عضّ الذراع أو ضرب الرأس)؟"},
    {"num": 18, "text": "هل اعتاد حمل أشياء (غير لعبة قماشية/بطانية مريحة) يجب أن يحملها دائمًا؟"},
    {"num": 19, "text": "هل لديه أصدقاء محددون أو صديق مقرّب؟"},

    # تعليمات قسم 4–5 سنوات (أو آخر 12 شهرًا لمن هم أصغر من 4 سنوات)
    {"num": 20, "text": "بين 4–5 سنوات: هل تحدّث معك بدافع الودّ (وليس للحصول على شيء)؟"},
    {"num": 21, "text": "بين 4–5 سنوات: هل قلدك تلقائيًا أنت/الآخرين في أنشطة منزلية؟"},
    {"num": 22, "text": "بين 4–5 سنوات: هل أشار بإصبعه لك ليريك أشياء (وليس لأنه يريدها)؟"},
    {"num": 23, "text": "بين 4–5 سنوات: هل استخدم إيماءات أخرى (غير الإشارة/سحب اليد) ليوصل ما يريد؟"},
    {"num": 24, "text": "بين 4–5 سنوات: هل هز رأسه ليعني “نعم”؟"},
    {"num": 25, "text": "بين 4–5 سنوات: هل هز رأسه ليعني “لا”؟"},
    {"num": 26, "text": "بين 4–5 سنوات: هل ينظر عادةً إلى وجهك عند الحديث/اللعب معك؟"},
    {"num": 27, "text": "بين 4–5 سنوات: هل يبتسم إذا ابتسم له أحد؟"},
    {"num": 28, "text": "بين 4–5 سنوات: هل يُريك أشياء تهمّه لجذب انتباهك؟"},
    {"num": 29, "text": "بين 4–5 سنوات: هل قدّم مشاركة أشياء (غير الطعام) معك؟"},
    {"num": 30, "text": "بين 4–5 سنوات: هل بدا أنه يريدك أن تشارك فرحته بشيء ما؟"},
    {"num": 31, "text": "بين 4–5 سنوات: هل حاول مواساتك إذا كنت حزينًا أو متألمًا؟"},
    {"num": 32, "text": "بين 4–5 سنوات: عند رغبته بشيء/مساعدة، هل نظر إليك واستخدم إيماءات مع أصوات/كلمات لجذب الانتباه؟"},
    {"num": 33, "text": "بين 4–5 سنوات: هل أظهر نطاقًا طبيعيًا من تعابير الوجه؟"},
    {"num": 34, "text": "بين 4–5 سنوات: هل انضم تلقائيًا وحاول تقليد الأفعال في الألعاب الاجتماعية؟"},
    {"num": 35, "text": "بين 4–5 سنوات: هل لعب لعبًا تخيّليًا؟"},
    {"num": 36, "text": "بين 4–5 سنوات: هل أبدى اهتمامًا بأطفال آخرين من نفس العمر لا يعرفهم؟"},
    {"num": 37, "text": "بين 4–5 سنوات: هل استجاب إيجابيًا لطفل آخر اقترب منه؟"},
    {"num": 38, "text": "بين 4–5 سنوات: إذا دخلت الغرفة وتحدثت دون مناداته، هل بحث عنك وأولى انتباهًا؟"},
    {"num": 39, "text": "بين 4–5 سنوات: هل لعب لعبًا تخيّليًا مع طفل آخر وكان واضحًا أنهما يفهمان تمثيل بعضهما؟"},
    {"num": 40, "text": "بين 4–5 سنوات: هل لعب بشكل تعاوني في ألعاب جماعية كالغميضة/ألعاب الكرة؟"},
]

@login_required
def scq_form(request, child_id):
    """عرض نموذج الاستبيان لوليّ الأمر + حفظ (POST)"""
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return HttpResponseForbidden("غير مصرح لك بإدخال هذا الاستبيان.")

    if request.method == "POST":
        # بيانات رأسية
        parent_full_name = request.POST.get("parent_full_name", "").strip()
        child_age_years = request.POST.get("child_age_years") or None
        child_sex = request.POST.get("child_sex", "").strip()
        residence = request.POST.get("residence", "").strip()
        child_diagnosis = request.POST.get("child_diagnosis", "").strip()

        # ربط اختياري بجلسة (إن أرسل session_id)
        session_id = request.POST.get("session_id")
        session = AssessmentSession.objects.filter(id=session_id, child=child).first() if session_id else None

        # الإجابات: answers[1]=نعم/لا
        answers = {}
        for item in SCQ_AR_ITEMS:
            key = f"answers[{item['num']}]"
            val = request.POST.get(key, "").strip()
            if val in ("نعم", "لا"):
                answers[str(item['num'])] = val

        sub = ParentSCQSubmission.objects.create(
            child=child,
            parent=request.user if request.user.user_type == "parent" else None,
            session=session,
            parent_full_name=parent_full_name,
            child_age_years=int(child_age_years) if child_age_years else None,
            child_sex=child_sex,
            residence=residence,
            child_diagnosis=child_diagnosis,
            answers=answers,
        )
        sub.recompute_counts()
        sub.save()
        return redirect("parent_portal:parent_scq_result", child_id=child.id, submission_id=sub.id)


    # GET: عرض النموذج
    # نمرر session_id لو جاينا من رابط فيه جلسة
    session_id = request.GET.get("session_id")
    session = AssessmentSession.objects.filter(id=session_id, child=child).first() if session_id else None

    return render(request, "parent_portal/scq_form.html", {
        "child": child,
        "items": SCQ_AR_ITEMS,
        "session": session,
    })

@login_required
def scq_result(request, child_id, submission_id):
    """عرض نتيجة استبيان SCQ المحفوظ"""
    child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    if not _can_view_child(request.user, child):
        return HttpResponseForbidden("غير مصرح بعرض هذه النتيجة.")

    sub = get_object_or_404(ParentSCQSubmission, id=submission_id, child=child)

    # نعيد ترتيب الإجابات حسب رقم السؤال
    answers = sub.answers or {}
    ordered = []
    for item in SCQ_AR_ITEMS:
        ordered.append({
            "num": item["num"],
            "text": item["text"],
            "answer": answers.get(str(item["num"]), "—"),
        })

    return render(request, "parent_portal/scq_result.html", {
        "child": child,
        "submission": sub,
        "ordered": ordered,
    })

# assessments/analytics.py
from collections import defaultdict
from django.db.models import Count, Q
from .models import (
    QuestionAnswer,
    EyeGazeSummary,
    Question,
    Skill,
    SkillGroup,
)

# أوزان الصعوبة (يمكن تعديلها لاحقًا)
DIFFICULTY_WEIGHTS = {1: 1.0, 2: 1.5, 3: 2.0}


# ============================= نظرة عامة على مستوى SkillGroup =============================
def compute_child_groups_overview(child, *, session=None):
    """
    نظرة عامة لكل "مجموعة مهارات" (SkillGroup) للطفل:
      - accuracy_pct: دقة موزونة بالصعوبة
      - attention_pct: انتباه WebGazer موزون بعدد العينات
      - counts: إجمالي/صح/غلط
      - level: strong / good / needs_improvement

    يمكن تمرير session لتصفية النتائج على جلسة بعينها فقط.
    """
    # إجابات الطفل (مفلترة بالجلسة إذا وُجدت)
    qa_qs = QuestionAnswer.objects.filter(user=child)
    if session:
        qa_qs = qa_qs.filter(session=session)

    # تجميع على مستوى المجموعة + الصعوبة
    qa_rows = qa_qs.values(
        "question__skill__group_id",
        "question__skill__group__name",
        "question__difficulty",
    ).annotate(
        total=Count("id"),
        correct=Count("id", filter=Q(is_correct=True)),
        wrong=Count("id", filter=Q(is_correct=False)),
    )

    # انتباه العين لكل سؤال (مفلتر بالجلسة/الطفل)
    gaze_qs = EyeGazeSummary.objects.all()
    if session:
        gaze_qs = gaze_qs.filter(session=session)
    else:
        gaze_qs = gaze_qs.filter(session__child=child)

    gaze_by_q = {
        g["question_id"]: g
        for g in gaze_qs.values("question_id", "samples", "on_task_samples", "attention_pct")
    }

    # تجميعة لكل مجموعة
    groups = defaultdict(
        lambda: {
            "group_id": None,
            "group_name": None,
            "counts": {"total": 0, "correct": 0, "wrong": 0},
            "weighted": {"num": 0.0, "den": 0.0},   # للدقة الموزونة
            "attention": {"num": 0.0, "den": 0.0},  # للانتباه الموزون بعدد العينات
        }
    )

    # الدقة الموزونة من الإجابات
    for r in qa_rows:
        gid = r["question__skill__group_id"]
        gname = r["question__skill__group__name"]
        diff = r["question__difficulty"]
        w = DIFFICULTY_WEIGHTS.get(diff, 1.0)

        d = groups[gid]
        d["group_id"] = gid
        d["group_name"] = gname
        d["counts"]["total"] += r["total"]
        d["counts"]["correct"] += r["correct"]
        d["counts"]["wrong"] += r["wrong"]
        d["weighted"]["num"] += r["correct"] * w
        d["weighted"]["den"] += r["total"] * w

    # انتباه موزون: نحدد لأي مجموعة ينتمي كل سؤال ثم نراكم
    qids_for_gaze = list(gaze_by_q.keys())
    if qids_for_gaze:
        # هات group لكل سؤال ظهر في الـ gaze
        q_to_group = dict(
            Question.objects.filter(id__in=qids_for_gaze).values_list("id", "skill__group_id")
        )
        group_names = dict(SkillGroup.objects.values_list("id", "name"))

        for qid, g in gaze_by_q.items():
            gid = q_to_group.get(qid)
            if not gid:
                continue
            d = groups[gid]
            if d["group_id"] is None:
                d["group_id"] = gid
                d["group_name"] = group_names.get(gid, "—")

            samples = g.get("samples") or 0
            att = g.get("attention_pct") or 0.0
            if samples > 0:
                d["attention"]["num"] += att * samples
                d["attention"]["den"] += samples

    # حساب النسب والتصنيف
    out = []
    for gid, d in groups.items():
        # دقة موزونة (fallback غير موزون لو مفيش أوزان)
        if d["weighted"]["den"] > 0:
            acc = (d["weighted"]["num"] / d["weighted"]["den"]) * 100.0
        else:
            total = d["counts"]["total"]
            acc = (d["counts"]["correct"] / total * 100.0) if total > 0 else 0.0

        # انتباه موزون
        att = (d["attention"]["num"] / d["attention"]["den"]) if d["attention"]["den"] > 0 else 0.0

        # تصنيف
        if acc < 60 or att < 45:
            level = "needs_improvement"
        elif acc >= 80 and att >= 65:
            level = "strong"
        else:
            level = "good"

        out.append(
            {
                "group_id": gid,
                "group_name": d["group_name"],
                "accuracy_pct": round(acc, 1),
                "attention_pct": round(att, 1),
                "counts": d["counts"],
                "level": level,
            }
        )

    # ترتيب: الأضعف أولًا
    out.sort(key=lambda x: (x["level"] != "needs_improvement", -x["accuracy_pct"], -x["attention_pct"]))
    return out


# ============================= نظرة عامة على مستوى Skill (موجودة لو بتحتاجها) =============================
def compute_child_skills_overview(child, *, session=None):
    """
    تُرجع ملخصًا قصيرًا لكل مهارة (Skill) للطفل:
      - accuracy_pct (دقة موزونة بالصعوبة)
      - attention_pct (WebGazer، موزونة بعدد العينات)
      - counts: إجمالي/صح/غلط
      - level: strong / good / needs_improvement

    ملاحظة: لو محتاج النظرة على مستوى SkillGroup استخدم compute_child_groups_overview.
    """
    qa_qs = QuestionAnswer.objects.filter(user=child)
    if session:
        qa_qs = qa_qs.filter(session=session)

    qa_rows = qa_qs.values(
        "question_id",
        "question__skill_id",
        "question__skill__name",
        "question__difficulty",
    ).annotate(
        total=Count("id"),
        correct=Count("id", filter=Q(is_correct=True)),
        wrong=Count("id", filter=Q(is_correct=False)),
    )

    gaze_qs = EyeGazeSummary.objects.all()
    if session:
        gaze_qs = gaze_qs.filter(session=session)
    else:
        gaze_qs = gaze_qs.filter(session__child=child)

    gaze_by_q = {
        g["question_id"]: g
        for g in gaze_qs.values("question_id", "samples", "on_task_samples", "attention_pct")
    }

    skills = defaultdict(
        lambda: {
            "skill_id": None,
            "skill_name": None,
            "counts": {"total": 0, "correct": 0, "wrong": 0},
            "weighted": {"num": 0.0, "den": 0.0},
            "attention": {"num": 0.0, "den": 0.0},
        }
    )

    for r in qa_rows:
        sid = r["question__skill_id"]
        sname = r["question__skill__name"]
        diff = r["question__difficulty"]
        w = DIFFICULTY_WEIGHTS.get(diff, 1.0)

        d = skills[sid]
        d["skill_id"] = sid
        d["skill_name"] = sname
        d["counts"]["total"] += r["total"]
        d["counts"]["correct"] += r["correct"]
        d["counts"]["wrong"] += r["wrong"]
        d["weighted"]["num"] += r["correct"] * w
        d["weighted"]["den"] += r["total"] * w

    for qid, g in gaze_by_q.items():
        try:
            q = Question.objects.only("id", "skill_id", "skill__name").get(id=qid)
        except Question.DoesNotExist:
            continue
        sid = q.skill_id
        sname = q.skill.name

        d = skills[sid]
        if d["skill_id"] is None:
            d["skill_id"] = sid
            d["skill_name"] = sname

        samples = g.get("samples") or 0
        att = g.get("attention_pct") or 0.0
        if samples > 0:
            d["attention"]["num"] += att * samples
            d["attention"]["den"] += samples

    out = []
    for sid, d in skills.items():
        if d["weighted"]["den"] > 0:
            acc = (d["weighted"]["num"] / d["weighted"]["den"]) * 100.0
        else:
            total = d["counts"]["total"]
            acc = (d["counts"]["correct"] / total * 100.0) if total > 0 else 0.0

        att = (d["attention"]["num"] / d["attention"]["den"]) if d["attention"]["den"] > 0 else 0.0

        if acc < 60 or att < 45:
            level = "needs_improvement"
        elif acc >= 80 and att >= 65:
            level = "strong"
        else:
            level = "good"

        out.append(
            {
                "skill_id": sid,
                "skill_name": d["skill_name"],
                "accuracy_pct": round(acc, 1),
                "attention_pct": round(att, 1),
                "counts": d["counts"],
                "level": level,
            }
        )

    out.sort(key=lambda x: (x["level"] != "needs_improvement", -x["accuracy_pct"], -x["attention_pct"]))
    return out


# ============================= تقرير تفصيلي لمهارة واحدة =============================
def compute_skill_detail(child, skill_id, *, session=None, limit_examples=5):
    """
    تقرير تفصيلي لمهارة واحدة:
      - accuracy_pct (موزونة بالصعوبة)
      - attention_pct (WebGazer، موزونة بعدد العينات)
      - distribution_by_difficulty: {1:{...}, 2:{...}, 3:{...}}
      - weakest_questions: يعرض نص السؤال (question_text) بدل ID
    """
    try:
        skill = Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return {"error": "skill_not_found"}

    qa_qs = QuestionAnswer.objects.filter(user=child, question__skill_id=skill_id)
    if session:
        qa_qs = qa_qs.filter(session=session)

    agg = qa_qs.values("question_id", "question__difficulty", "is_correct").annotate(
        cnt=Count("id")
    )

    # توزيع حسب الصعوبة
    dist = {
        1: {"total": 0, "correct": 0, "wrong": 0, "acc_pct": 0.0},
        2: {"total": 0, "correct": 0, "wrong": 0, "acc_pct": 0.0},
        3: {"total": 0, "correct": 0, "wrong": 0, "acc_pct": 0.0},
    }

    weighted_num = 0.0
    weighted_den = 0.0
    per_q = defaultdict(lambda: {"total": 0, "correct": 0, "wrong": 0, "diff": None})

    for r in agg:
        qid = r["question_id"]
        diff = r["question__difficulty"]
        c = r["cnt"]

        per_q[qid]["diff"] = diff
        per_q[qid]["total"] += c
        if r["is_correct"]:
            per_q[qid]["correct"] += c
            dist[diff]["correct"] += c
        else:
            per_q[qid]["wrong"] += c
            dist[diff]["wrong"] += c
        dist[diff]["total"] += c

    for diff in (1, 2, 3):
        d = dist[diff]
        if d["total"] > 0:
            d["acc_pct"] = round(d["correct"] / d["total"] * 100.0, 1)
        w = DIFFICULTY_WEIGHTS.get(diff, 1.0)
        weighted_num += d["correct"] * w
        weighted_den += d["total"] * w

    acc_pct = round((weighted_num / weighted_den * 100.0), 1) if weighted_den > 0 else 0.0

    # انتباه داخل هذه المهارة
    gaze_qs = EyeGazeSummary.objects.all()
    if session:
        gaze_qs = gaze_qs.filter(session=session)
    else:
        gaze_qs = gaze_qs.filter(session__child=child)
    gaze_qs = gaze_qs.filter(question__skill_id=skill_id)

    gaze_map = {
        g["question_id"]: g
        for g in gaze_qs.values("question_id", "samples", "attention_pct", "on_task_samples")
    }

    att_num = 0.0
    att_den = 0.0
    for qid, g in gaze_map.items():
        s = g.get("samples") or 0
        a = g.get("attention_pct") or 0.0
        if s > 0:
            att_num += a * s
            att_den += s
    attention_pct = round((att_num / att_den), 1) if att_den > 0 else 0.0

    # --- نصوص الأسئلة بدل أرقامها ---
    qids = list(per_q.keys())
    q_texts = dict(Question.objects.filter(id__in=qids).values_list("id", "question_text"))

    weakest = []
    for qid, st in per_q.items():
        total = st["total"]
        corr = st["correct"]
        acc_q = (corr / total * 100.0) if total > 0 else 0.0
        g = gaze_map.get(qid)
        att_q = (g.get("attention_pct", 0.0) if g else 0.0)

        weakest.append(
            {
                "question_text": (q_texts.get(qid) or "—"),
                "difficulty": st["diff"],
                "acc_pct": round(acc_q, 1),
                "attention_pct": round(att_q, 1),
            }
        )

    # الأقل دقة ثم الأقل انتباهًا ثم الأصعب
    weakest.sort(
        key=lambda x: (x["acc_pct"], x["attention_pct"], -x["difficulty"] if x["difficulty"] else 0)
    )
    if limit_examples:
        weakest = weakest[:limit_examples]

    # مستوى عام
    if acc_pct < 60 or attention_pct < 45:
        level = "needs_improvement"
    elif acc_pct >= 80 and attention_pct >= 65:
        level = "strong"
    else:
        level = "good"

    return {
        "skill_id": skill.id,
        "skill_name": skill.name,
        "accuracy_pct": acc_pct,
        "attention_pct": attention_pct,
        "level": level,
        "distribution_by_difficulty": dist,
        "weakest_questions": weakest,
    }











# === ترند الجلسات للطفل: دقة/انتباه بمرور الوقت ===
def compute_child_session_trend(child, max_points=24):
    """
    يرجّع قائمة مرتبة زمنياً لكل الجلسات المُكتملة:
      [{ "session_id": 123, "label": "2025-09-18", "accuracy_pct": 82.0, "attention_pct": 56.3, "duration_sec": 1500 }, ...]
    attention_pct محسوبة كمعدل موزون بعدد العينات من EyeGazeSummary.
    """
    from .models import AssessmentSession, EyeGazeSummary

    sessions = (AssessmentSession.objects
                .filter(child=child, status="completed")
                .order_by("started_at")
               )

    # اجمع الانتباه موزوناً بالعينات لكل جلسة
    att_num = {}  # session_id -> sum(attention_pct * samples)
    att_den = {}  # session_id -> sum(samples)
    gaze_rows = EyeGazeSummary.objects.filter(session__in=sessions).values("session_id", "samples", "attention_pct")
    for g in gaze_rows:
        sid = g["session_id"]
        s = g.get("samples") or 0
        a = g.get("attention_pct") or 0.0
        if s > 0:
            att_num[sid] = att_num.get(sid, 0.0) + a * s
            att_den[sid] = att_den.get(sid, 0.0) + s

    trend = []
    for s in sessions:
        acc = 0.0
        if s.total_questions and s.total_questions > 0:
            acc = round((s.correct_count / s.total_questions) * 100.0, 1)

        den = att_den.get(s.id, 0.0)
        att = round(att_num[s.id] / den, 1) if den > 0 else 0.0

        label = (s.started_at.astimezone().strftime("%Y-%m-%d") if hasattr(s.started_at, "astimezone")
                 else s.started_at.strftime("%Y-%m-%d"))

        trend.append({
            "session_id": s.id,
            "label": label,
            "accuracy_pct": acc,
            "attention_pct": att,
            "duration_sec": s.duration_seconds,
        })

    if max_points and len(trend) > max_points:
        trend = trend[-max_points:]

    return trend

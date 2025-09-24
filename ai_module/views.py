from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from assessments.models import Skill, Question , QuestionAnswer ,EyeGazeSample, EyeGazeSummary, AssessmentSession
import json
import random
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_POST ,require_GET
import time




@csrf_exempt
@login_required
def generate_question(request):
    time.sleep(2)
    if request.method != "POST":
        return JsonResponse({"error": "POST فقط مسموح"}, status=405)

    try:
        session = request.session.get("ai_session")
        if not session:
            print("❌ لا توجد جلسة ai_session في السيشن")
            return JsonResponse({"error": "لا توجد جلسة نشطة"}, status=400)

        skill_ids = session.get("skill_ids", [])
        current_index = session.get("current_skill_index", 0)
        current_difficulty = session.get("current_difficulty", 1)

        print("📘 قائمة المهارات:", skill_ids)
        print("📍 الفهرس الحالي:", current_index)
        print("📊 مستوى الصعوبة:", current_difficulty)

        # تنظيف المهارات المحذوفة
        valid_skills = Skill.objects.filter(id__in=skill_ids).values_list('id', flat=True)
        skill_ids = list(valid_skills)
        session["skill_ids"] = skill_ids

        print("✅ المهارات بعد التنظيف:", skill_ids)

        while current_index < len(skill_ids):
            skill_id = skill_ids[current_index]
            try:
                skill = Skill.objects.get(id=skill_id)
                print(f"🎯 تم اختيار المهارة ID = {skill_id} - {skill.name}")

                questions = list(skill.questions.filter(difficulty=current_difficulty))
                print(f"🧠 عدد الأسئلة المتاحة لمستوى {current_difficulty} = {len(questions)}")

                if questions:
                    question = random.choice(questions)

                    session["current_skill_index"] = current_index
                    session["current_question_id"] = question.id
                    request.session.update({"ai_session": session})
                    request.session.modified = True

                    print("✅ تم اختيار سؤال ID:", question.id)

                    return JsonResponse({
                        "question_text": question.question_text,
                        "question_type": question.question_type,
                        "image": question.image.url if question.image else None,
                        "options": question.options,
                        "difficulty": question.difficulty,
                        "question_id": question.id,
                        "video": question.video.url if question.video else None,
                    }, json_dumps_params={"ensure_ascii": False})

                else:
                    print(f"⚠️ لا يوجد أسئلة للمهارة {skill.name} - نتخطاها")
                    current_index += 1
                    session["current_difficulty"] = 1
                    session["wrong_attempts"] = 0
                    continue

            except Skill.DoesNotExist:
                print(f"⚠️ المهارة ID = {skill_id} غير موجودة. الانتقال للتي تليها.")
                current_index += 1

        print("🚫 لم يتم العثور على أي مهارة صالحة بأسئلة")
        return JsonResponse({"end_of_session": True}, status=200)

    except Exception as e:
        print("🔥 استثناء:", str(e))
        return JsonResponse({"error": "خطأ في السيرفر", "details": str(e)}, status=500)












from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from assessments.models import Question, QuestionAnswer

@csrf_exempt
@login_required
def verify_answer(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST فقط مسموح"}, status=405)

    try:
        data = json.loads(request.body)
        answer = data.get("answer")

        session = request.session.get("ai_session")
        if not session:
            return JsonResponse({"error": "لا توجد جلسة نشطة"}, status=400)

        question_id = session.get("current_question_id")
        if not all([answer, question_id]):
            return JsonResponse({"error": "answer و question_id مطلوبين"}, status=400)

        user = request.user
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return JsonResponse({"error": "السؤال غير موجود"}, status=404)

        if question.question_type == "drag_and_drop":
            try:
                correct_options = question.options  # [{'image':..., 'target':...}]
                correct_map = {}
                for opt in correct_options:
                    target = opt["target"]; image = opt["image"]
                    correct_map.setdefault(target, []).append(image)

                is_correct = True
                for target in correct_map:
                    correct_images = sorted(correct_map.get(target, []))
                    user_images = sorted((answer or {}).get(target, []))
                    if correct_images != user_images:
                        is_correct = False
                        break

                if set((answer or {}).keys()) != set(correct_map.keys()):
                    is_correct = False
            except Exception:
                is_correct = False
        else:
            is_correct = (str(answer).strip() == str(question.correct_answer).strip())

        db_session = None
        db_session_id = session.get("db_session_id")
        if db_session_id:
            db_session = AssessmentSession.objects.filter(
                id=db_session_id, child=request.user
            ).first()

        QuestionAnswer.objects.create(
            user=user,
            question=question,
            is_correct=is_correct,
            session=db_session  # ADDED
        )

        if db_session:
            db_session.total_questions += 1
            if is_correct:
                db_session.correct_count += 1
            else:
                db_session.wrong_count += 1
            db_session.state_snapshot = {
                "skill_ids": session.get("skill_ids", []),
                "current_skill_index": session.get("current_skill_index", 0),
                "current_difficulty": session.get("current_difficulty", 1),
                "wrong_attempts": session.get("wrong_attempts", 0),
            }
            db_session.save()
        # ======== /ADDED ========

        if is_correct:
            if session["current_difficulty"] < 3:
                session["current_difficulty"] += 1
            else:
                session["current_skill_index"] += 1
                session["current_difficulty"] = 1
                session["wrong_attempts"] = 0
        else:
            session["wrong_attempts"] = session.get("wrong_attempts", 0) + 1
            if session["wrong_attempts"] >= 2:
                session["current_skill_index"] += 1
                session["current_difficulty"] = 1
                session["wrong_attempts"] = 0

        request.session.update({"ai_session": session})
        request.session.modified = True

        return JsonResponse({"correct": is_correct})

    except Exception as e:
        return JsonResponse({"error": "خطأ في السيرفر", "details": str(e)}, status=500)







@csrf_exempt
@require_POST
@login_required
def gaze_ingest(request):
    if request.user.user_type != "child":
        return JsonResponse({"ok": False, "error": "مسموح للأطفال فقط"}, status=403)

    try:
        body = json.loads(request.body or "{}")
        samples = body.get("samples", [])
        if not isinstance(samples, list) or not samples:
            return JsonResponse({"ok": True, "saved": 0})
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON غير صحيح"}, status=400)

    sess = request.session.get("ai_session", {})
    db_session = None
    if sess.get("db_session_id"):
        db_session = AssessmentSession.objects.filter(id=sess["db_session_id"], child=request.user).first()

    qobj = None
    if sess.get("current_question_id"):
        qobj = Question.objects.filter(id=sess["current_question_id"]).first()

    objs = []
    now = timezone.now()
    for s in samples:
        t_ms = s.get("t")
        ts = now if not t_ms else timezone.make_aware(timezone.datetime.fromtimestamp(t_ms/1000.0))
        objs.append(EyeGazeSample(
            user=request.user,
            session=db_session,
            question=qobj,
            t=ts,
            x=int(s.get("x", 0)),
            y=int(s.get("y", 0)),
            on_task=bool(s.get("on_task", False)),
        ))
    EyeGazeSample.objects.bulk_create(objs, batch_size=500)

    if db_session and qobj:
        total = EyeGazeSample.objects.filter(session=db_session, question=qobj).count()
        on_task = EyeGazeSample.objects.filter(session=db_session, question=qobj, on_task=True).count()
        pct = (on_task/total*100.0) if total>0 else 0.0
        summary, _ = EyeGazeSummary.objects.get_or_create(session=db_session, question=qobj,
            defaults={'samples': total, 'on_task_samples': on_task, 'attention_pct': pct})
        summary.samples = total
        summary.on_task_samples = on_task
        summary.attention_pct = pct
        summary.save()

    return JsonResponse({"ok": True, "saved": len(objs)})




@csrf_exempt
@require_POST
@login_required
def end_session(request):
    """
    ينهي الجلسة الحالية (إن وجدت) ويحوّل حالتها إلى completed
    ويعيد المدة في الاستجابة، ثم يمسح ai_session من الـ session.
    الدالة idempotent: لا تفشل لو كانت الجلسة مختومة مسبقًا.
    """
    sess = request.session.get("ai_session")
    session_obj = None

    if sess and sess.get("db_session_id"):
        session_obj = AssessmentSession.objects.filter(
            id=sess["db_session_id"], child=request.user
        ).first()

        if session_obj and session_obj.status == "active":
            session_obj.status = "completed"
            session_obj.ended_at = timezone.now()
            session_obj.save(update_fields=["status", "ended_at"])

        request.session.pop("ai_session", None)
        request.session.modified = True

    else:
        session_obj = (AssessmentSession.objects
                       .filter(child=request.user)
                       .order_by("-started_at", "-id")
                       .first())
        if not session_obj:
            return JsonResponse({"ok": False, "error": "لا توجد جلسة نشطة"}, status=400)

        if session_obj.status == "active":
            session_obj.status = "completed"
            session_obj.ended_at = timezone.now()
            session_obj.save(update_fields=["status", "ended_at"])

    payload = {"ok": True}
    if session_obj:
        payload.update({
            "session_id": session_obj.id,
            "status": session_obj.status,
            "started_at": session_obj.started_at,
            "ended_at": session_obj.ended_at,
            "duration_seconds": session_obj.duration_seconds,  
            "duration_human": session_obj.duration_human,     
        })

    return JsonResponse(payload)




@require_GET
@login_required
def get_progress(request):
    """
    يعرض تقدّم الجلسة الحالية:
    - من الـ session (الفهرس/الصعوبة/محاولات الخطأ)
    - ومن سجل AssessmentSession (إجمالي الأسئلة/صح/غلط/الحالة) إن وُجد.
    """
    sess = request.session.get("ai_session")
    progress = {
        "has_session": bool(sess),
        "current_skill_index": (sess or {}).get("current_skill_index"),
        "current_difficulty": (sess or {}).get("current_difficulty"),
        "wrong_attempts": (sess or {}).get("wrong_attempts"),
        "skills_count": len((sess or {}).get("skill_ids", [])),
    }

    totals = {}
    db_session_id = (sess or {}).get("db_session_id")
    if db_session_id:
        db = AssessmentSession.objects.filter(id=db_session_id, child=request.user).first()
        if db:
            totals = {
                "total_questions": db.total_questions,
                "correct_count": db.correct_count,
                "wrong_count": db.wrong_count,
                "status": db.status,
                "started_at": db.started_at,
                "ended_at": db.ended_at,
                "elapsed_seconds": db.duration_seconds,
                "elapsed_human": db.duration_human,
            }

    return JsonResponse({"progress": progress, "totals": totals}, json_dumps_params={"ensure_ascii": False})
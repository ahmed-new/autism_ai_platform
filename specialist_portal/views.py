# specialist_portal/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import LinkRequest
from assessments.models import AssessmentSession
from django.db.models import Prefetch ,Q
from accounts.models import CustomUser


@login_required
def specialist_home(request):
    if request.user.user_type != "specialist":
        return render(request, "unauthorized.html")

    
       # جلسات مرتّبة ومخففة الحقول
    sessions_qs = (
        AssessmentSession.objects
        .only("id", "status", "started_at", "ended_at")
        .order_by("-started_at", "-id")
    )
    patients = (
        CustomUser.objects
        .filter(specialist=request.user, user_type="child")
        .select_related("parent")
        .prefetch_related(Prefetch("assessment_sessions", queryset=sessions_qs))
    )


    pending = LinkRequest.objects.filter(specialist=request.user, status="pending")
    return render(request, "specialist_portal/home.html", {
        "patients": patients,
        "pending": pending,
    })

@login_required
def approve_link(request, pk):
    if request.user.user_type != "specialist":
        return render(request, "unauthorized.html")

    req = get_object_or_404(LinkRequest, pk=pk, specialist=request.user)
    child = req.child

    # لو الطفل بالفعل مرتبط بأخصائي، ارفض الطلب تلقائيًا
    if child.specialist_id and child.specialist_id != request.user.id:
        req.status = "rejected"
        req.decided_at = timezone.now()
        req.note = "الطفل مرتبط بأخصائي آخر."
        req.save()
        messages.error(request, "لا يمكن قبول الطلب: الطفل مرتبط بأخصائي آخر.")
        return redirect("specialist_home")

    # اربط الطفل، وعدّل حالة الطلب
    child.specialist = request.user
    child.save(update_fields=["specialist"])

    req.status = "approved"
    req.decided_at = timezone.now()
    req.save()

    # ارفض أي طلبات أخرى معلّقة لنفس الطفل
    LinkRequest.objects.filter(child=child, status="pending").exclude(pk=req.pk).update(
        status="rejected", decided_at=timezone.now(), note="تم قبول طلب آخر."
    )

    messages.success(request, f"تم ربط الطفل {child.username} بك بنجاح.")
    return redirect("specialist_home")


@login_required
def reject_link(request, pk):
    if request.user.user_type != "specialist":
        return render(request, "unauthorized.html")

    req = get_object_or_404(LinkRequest, pk=pk, specialist=request.user)
    req.status = "rejected"
    req.decided_at = timezone.now()
    req.save()
    messages.info(request, "تم رفض الطلب.")
    return redirect("specialist_home")

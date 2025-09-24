from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import CustomUser
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from specialist_portal.models import LinkRequest
from assessments.models import AssessmentSession
from assessments.models import ParentSCQSubmission  # ← مهم
from django.db.models import Prefetch ,Q



@login_required
def parent_home(request):
    # الأطفال المرتبطون بالوالد
    children = list(
        CustomUser.objects
        .filter(parent=request.user, user_type="child")
        .select_related("specialist")
        .prefetch_related(
            Prefetch(
                "assessment_sessions",
                queryset=AssessmentSession.objects.order_by("-started_at", "-id"),
            )
        )
    )

    # جهّز خصائص جاهزة للاستخدام في القالب
    for c in children:
        # آخر جلسة مكتملة
        c.last_completed_session = next(
            (s for s in c.assessment_sessions.all() if s.status == "completed"),
            None
        )
        # آخر SCQ (اختياري)
        c.latest_scq = (
            ParentSCQSubmission.objects
            .filter(child=c)
            .order_by("-created_at")
            .first()
        )
        # طلب متابعة معلّق (اختياري)
        c.pending_link = (
            LinkRequest.objects
            .filter(child=c, status="pending")
            .order_by("-created_at")
            .first()
        )

    return render(request, "parent_portal/home.html", {
        "children": children,
    })





@login_required
def create_child(request):
    if request.user.user_type != "parent":
        return render(request, "unauthorized.html")

    specialists = CustomUser.objects.filter(user_type='specialist')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email    = request.POST.get("email") or ""
        specialist_id = request.POST.get("specialist_id") or ""

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "اسم المستخدم موجود بالفعل.")
            return render(request, "parent_portal/create_child.html", {"specialists": specialists})

        child = CustomUser.objects.create(
            username=username,
            email=email,
            user_type="child",
            parent=request.user,
            password=make_password(password),
        )

        # لو اختار أخصائي
        if specialist_id:
            try:
                sp = CustomUser.objects.get(id=specialist_id, user_type="specialist")
            except CustomUser.DoesNotExist:
                messages.warning(request, "الأخصائي المحدد غير موجود.")
            else:
                # لو الطفل بالفعل له أخصائي، لا تنشئ طلب.
                if child.specialist_id:
                    messages.info(request, "الطفل لديه أخصائي بالفعل، لم يتم إرسال طلب.")
                else:
                    LinkRequest.objects.get_or_create(
                        child=child,
                        specialist=sp,
                        defaults={"created_by": request.user}
                    )
                    messages.success(request, f"تم إرسال طلب متابعة إلى الأخصائي: {sp.username}")

        messages.success(request, "تم إنشاء حساب الطفل بنجاح.")
        return redirect("parent_portal:parent_home")


    return render(request, "parent_portal/create_child.html", {
        "specialists": specialists
    })






@login_required
def assign_specialist(request, child_id):
    # تأكد أن الطفل تابع لهذا الأب (أو موظّف/أدمن)
    if request.user.is_staff or request.user.is_superuser:
        child = get_object_or_404(CustomUser, id=child_id, user_type="child")
    else:
        child = get_object_or_404(
            CustomUser, id=child_id, user_type="child", parent=request.user
        )

    if request.method == "POST":
        spec_id = request.POST.get("specialist_id")
        sp = get_object_or_404(
            CustomUser, id=spec_id, user_type="specialist", is_active=True
        )

        # ★ أنشئ/استرجع طلب الربط (دعوة)
        lr, created = LinkRequest.objects.get_or_create(
            child=child,
            specialist=sp,
            defaults={"created_by": request.user}
        )

        # لو عندك حقل status قديم مش "pending"، تقدر تحدثه هنا حسب لوجيكك
        if not created and getattr(lr, "status", "pending") != "pending":
            # مثال: إعادة فتح الطلب (اختياري)
            try:
                lr.status = "pending"
                lr.save(update_fields=["status"])
            except Exception:
                pass

        if created:
            messages.success(request, f"تم إرسال طلب متابعة إلى الأخصائي: {sp.username}")
        else:
            messages.info(request, f"هناك طلب سابق لهذا الأخصائي — حالته الحالية: {getattr(lr, 'status', 'pending')}")

        return redirect("parent_portal:parent_home")

    # GET: عرض قائمة الأخصائيين مع بحث اختياري
    q = (request.GET.get("q") or "").strip()
    specialists = CustomUser.objects.filter(user_type="specialist", is_active=True)
    if q:
        specialists = specialists.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )
    specialists = specialists.order_by("username")[:200]

    return render(
        request,
        "parent_portal/assign_specialist.html",
        {"child": child, "specialists": specialists, "q": q},)



# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CustomUserCreationForm
from .models import CustomUser
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # سيحترم clean() وقيود الأنواع
            return redirect("login")
    else:
        form = CustomUserCreationForm(initial={"user_type":"child"})
    return render(request, "accounts/register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.user_type == "child":
                return redirect("child_home")
            elif user.user_type == "parent":
                return redirect("parent_portal:parent_home")
            elif user.user_type == "specialist":
                return redirect("specialist_home")
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    messages.info(request, " تم تسجيل الخروج ")
    return redirect("login")


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        messages.success(self.request, "تم تغيير كلمة المرور بنجاح")
        return super().form_valid(form)


def landing_view(request):
    # لو المستخدم داخل بالفعل، وديه للوحة المناسبة
    if request.user.is_authenticated:
        u = request.user
        if getattr(u, "user_type", None) == "parent":
            return redirect("parent_portal:parent_home")
        elif getattr(u, "user_type", None) == "specialist":
            return redirect("specialist_home")   
        elif getattr(u, "user_type", None) == "child":
            return redirect("child_home")       
  
    return render(request, "landing.html")

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from memorials.models import Donation, Memorial

from .forms import SignUpForm


def signup(request):
    """Register a new public user and log them in."""
    if request.user.is_authenticated:
        return redirect("cemeteries:search")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.username}. Your account is ready.")
        return redirect("accounts:profile")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def profile(request):
    """Show the user's memorials and the donations they have made."""
    return render(
        request,
        "registration/profile.html",
        {
            "memorials": Memorial.objects.filter(owner=request.user).select_related("grave"),
            "donations": Donation.objects.filter(donor=request.user).select_related("memorial"),
        },
    )

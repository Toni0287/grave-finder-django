from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cemeteries.models import Grave

from .forms import PRESET_AMOUNTS, CondolenceForm, DonationForm, MemorialForm
from .models import Donation, Memorial
from .payments import PayFastGateway


def memorial_list(request):
    memorials = Memorial.objects.published().select_related("grave__cemetery")
    return render(request, "memorials/memorial_list.html", {"memorials": memorials})


def memorial_detail(request, pk):
    memorial = get_object_or_404(Memorial.objects.visible_to(request.user), pk=pk)
    completed = memorial.completed_donations()
    return render(
        request,
        "memorials/memorial_detail.html",
        {
            "memorial": memorial,
            "can_edit": memorial.can_edit(request.user),
            "condolences": memorial.condolences.all(),
            "condolence_form": CondolenceForm(),
            "donation_total": memorial.donation_total(),
            "donor_count": completed.count(),
            "recent_donations": completed[:5],
            "preset_amounts": PRESET_AMOUNTS,
        },
    )


@login_required
def memorial_create(request):
    initial = {}
    grave_id = request.GET.get("grave")
    if grave_id and grave_id.isdigit():
        grave = Grave.objects.active().filter(pk=grave_id).first()
        if grave:
            initial = {"grave": grave, "full_name": grave.full_name, "death_date": grave.date_of_death}

    form = MemorialForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        memorial = form.save(commit=False)
        memorial.owner = request.user
        memorial.save()
        messages.success(request, "Memorial saved as a draft. Publish it when you are ready.")
        return redirect(memorial)
    return render(request, "memorials/memorial_form.html", {"form": form, "title": "Create a memorial"})


def _editable_memorial(request, pk):
    memorial = get_object_or_404(Memorial, pk=pk)
    if not memorial.can_edit(request.user):
        raise PermissionDenied
    return memorial


@login_required
def memorial_update(request, pk):
    memorial = _editable_memorial(request, pk)
    form = MemorialForm(request.POST or None, instance=memorial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Memorial updated.")
        return redirect(memorial)
    return render(
        request, "memorials/memorial_form.html", {"form": form, "title": f"Edit {memorial.full_name}"}
    )


@login_required
@require_POST
def memorial_set_status(request, pk):
    """Publish, unpublish or archive a memorial."""
    memorial = _editable_memorial(request, pk)
    status = request.POST.get("status")
    if status not in Memorial.Status.values:
        return HttpResponseBadRequest("Unknown status")
    memorial.status = status
    memorial.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Memorial is now {memorial.get_status_display().lower()}.")
    return redirect(memorial)


@require_POST
def condolence_create(request, pk):
    memorial = get_object_or_404(Memorial.objects.published(), pk=pk)
    form = CondolenceForm(request.POST)
    if form.is_valid():
        condolence = form.save(commit=False)
        condolence.memorial = memorial
        condolence.save()
        messages.success(request, "Thank you. Your message has been added.")
    else:
        messages.error(request, "Please add your name and a message.")
    return redirect(memorial)


def donate(request, pk):
    """Collect donor details, then complete (demo) or hand over to PayFast."""
    memorial = get_object_or_404(Memorial.objects.published(), pk=pk, donations_enabled=True)
    initial = {}
    if request.GET.get("amount", "").isdigit():
        initial["amount"] = request.GET["amount"]
    if request.user.is_authenticated:
        initial.update(
            donor_name=request.user.get_full_name() or request.user.username,
            donor_email=request.user.email,
        )

    form = DonationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        donation = form.save(commit=False)
        donation.memorial = memorial
        if request.user.is_authenticated:
            donation.donor = request.user
        donation.save()

        gateway = PayFastGateway()
        if gateway.is_demo:
            donation.mark_completed(payment_id="DEMO")
            return redirect("memorials:donation_thanks", reference=donation.reference)

        fields = gateway.checkout_fields(
            donation,
            return_url=request.build_absolute_uri(
                reverse("memorials:donation_thanks", args=[donation.reference])
            ),
            cancel_url=request.build_absolute_uri(memorial.get_absolute_url()),
            notify_url=request.build_absolute_uri(reverse("memorials:payfast_notify")),
        )
        return render(
            request,
            "memorials/payfast_redirect.html",
            {"action": gateway.process_url, "fields": fields, "donation": donation},
        )

    return render(
        request,
        "memorials/donate.html",
        {
            "memorial": memorial,
            "form": form,
            "preset_amounts": PRESET_AMOUNTS,
            "fee_percent": int(settings.DONATION_PLATFORM_FEE * 100),
        },
    )


def donation_thanks(request, reference):
    donation = get_object_or_404(Donation.objects.select_related("memorial"), reference=reference)
    return render(request, "memorials/donation_thanks.html", {"donation": donation})


@csrf_exempt
@require_POST
def payfast_notify(request):
    """PayFast's server-to-server payment notification (ITN)."""
    gateway = PayFastGateway()
    if not gateway.is_valid_notification(request.POST):
        return HttpResponseBadRequest("Invalid signature")

    donation = get_object_or_404(Donation, reference=request.POST.get("m_payment_id"))
    if request.POST.get("amount_gross") != f"{donation.amount:.2f}":
        return HttpResponseBadRequest("Amount mismatch")

    if request.POST.get("payment_status") == "COMPLETE":
        donation.mark_completed(payment_id=request.POST.get("pf_payment_id", ""))
    elif donation.status == Donation.Status.PENDING:
        donation.status = Donation.Status.FAILED
        donation.save(update_fields=["status"])
    return HttpResponse("OK")

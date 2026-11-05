from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import GraveForm, GraveSearchForm
from .models import Cemetery, Grave
from .stats import DashboardStats

RESULTS_PER_PAGE = 20


def is_cemetery_staff(user):
    return user.is_authenticated and user.is_cemetery_staff


staff_required = user_passes_test(is_cemetery_staff)


def search(request):
    """Home page: search form, paginated results and a map of matches."""
    form = GraveSearchForm(request.GET or None)
    page = None
    breakdown = []
    if form.has_filters():
        results = form.filter(Grave.objects.active().select_related("cemetery"))
        breakdown = (
            results.values("cemetery__name").annotate(count=Count("id")).order_by("-count")
        )
        page = Paginator(results, RESULTS_PER_PAGE).get_page(request.GET.get("page"))

    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "cemeteries/search.html",
        {
            "form": form,
            "page": page,
            "breakdown": breakdown,
            "querystring": query.urlencode(),
            "markers": [g.map_marker() for g in page] if page else [],
            "totals": DashboardStats().totals(),
        },
    )


def grave_detail(request, pk):
    """One grave with its map, directions and any public memorial."""
    grave = get_object_or_404(Grave.objects.active().select_related("cemetery"), pk=pk)
    memorial = grave.memorials.filter(status="active").first()
    return render(
        request,
        "cemeteries/grave_detail.html",
        {
            "grave": grave,
            "memorial": memorial,
            "marker": grave.map_marker(),
            "entrance": {"lat": grave.cemetery.latitude, "lng": grave.cemetery.longitude},
        },
    )


def grave_print(request, pk):
    """Printer-friendly record of a grave."""
    grave = get_object_or_404(Grave.objects.active().select_related("cemetery"), pk=pk)
    return render(request, "cemeteries/grave_print.html", {"grave": grave, "now": timezone.now()})


def cemetery_list(request):
    cemeteries = Cemetery.objects.annotate(grave_count=Count("graves"))
    return render(
        request,
        "cemeteries/cemetery_list.html",
        {
            "cemeteries": cemeteries,
            "markers": [
                {"name": c.name, "lat": c.latitude, "lng": c.longitude, "type": c.type}
                for c in cemeteries
            ],
        },
    )


def dashboard(request):
    stats = DashboardStats()
    per_year = stats.burials_per_year()
    return render(
        request,
        "cemeteries/dashboard.html",
        {
            "totals": stats.totals(),
            "per_cemetery": stats.per_cemetery(),
            "per_year": per_year,
            "max_per_year": max((row["count"] for row in per_year), default=1),
            "plot_sizes": stats.plot_sizes(),
        },
    )


@login_required
@staff_required
def grave_create(request):
    form = GraveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        grave = form.save()
        messages.success(request, f"Added {grave.full_name}.")
        return redirect(grave)
    return render(request, "cemeteries/grave_form.html", {"form": form, "title": "Add a grave"})


@login_required
@staff_required
def grave_update(request, pk):
    grave = get_object_or_404(Grave.objects.active(), pk=pk)
    form = GraveForm(request.POST or None, instance=grave)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Grave record updated.")
        return redirect(grave)
    return render(
        request, "cemeteries/grave_form.html", {"form": form, "title": f"Edit {grave.full_name}"}
    )


@login_required
@staff_required
def grave_delete(request, pk):
    """Soft delete: the record is hidden but kept for the audit trail."""
    grave = get_object_or_404(Grave.objects.active(), pk=pk)
    if request.method == "POST":
        grave.deleted_at = timezone.now()
        grave.save(update_fields=["deleted_at"])
        messages.success(request, f"{grave.full_name} has been removed from search.")
        return redirect("cemeteries:search")
    return render(request, "cemeteries/grave_confirm_delete.html", {"grave": grave})

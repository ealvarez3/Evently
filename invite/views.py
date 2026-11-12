import mimetypes
import os
import re

from django import forms
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.utils._os import safe_join
from django.shortcuts import aget_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Event, Family, GrowthPhoto, ItineraryItem, SongSuggestion, VaultPhoto

MAX_PHOTOS = 10
MAX_PHOTO_BYTES = 15 * 1024 * 1024


def _back(token, anchor, query=""):
    return redirect(reverse("invitation", args=[token]) + query + anchor)


async def invitation(request, token=None):
    event = await Event.objects.afirst()
    if event is None:
        return HttpResponse("La invitación está en preparación. Crea el evento en /admin/.", status=503)
    family = await aget_object_or_404(Family, token=token) if token else None
    # querysets are evaluated here: templates can't hit the DB from an async view
    ctx = {
        "event": event,
        "family": family,
        "itinerary": [i async for i in ItineraryItem.objects.order_by("time")],
        "growth": [p async for p in GrowthPhoto.objects.order_by("order", "id")],
        "songs": [s async for s in SongSuggestion.objects.select_related("family").order_by("-created")[:30]],
        "vault": [],
    }
    if event.vault_open:
        ctx["vault"] = [
            p async for p in VaultPhoto.objects.filter(visible=True).select_related("family").order_by("-created")
        ]
    return render(request, "invite/invitation.html", ctx)


@require_POST
async def rsvp(request, token):
    family = await aget_object_or_404(Family, token=token)
    answer = request.POST.get("answer")
    if answer in (Family.Status.YES, Family.Status.NO):
        family.status, family.responded_at = answer, timezone.now()
        await family.asave(update_fields=["status", "responded_at"])
    return _back(token, "#asistencia")


@require_POST
async def song(request, token):
    family = await aget_object_or_404(Family, token=token)
    title = request.POST.get("title", "").strip()[:120]
    if title:
        await SongSuggestion.objects.acreate(
            family=family, title=title, artist=request.POST.get("artist", "").strip()[:120]
        )
    return _back(token, "#canciones")


@require_POST
async def vault_upload(request, token):
    family = await aget_object_or_404(Family, token=token)
    event = await Event.objects.afirst()
    if event is None or not event.vault_open:
        return HttpResponseForbidden("La bóveda todavía está cerrada.")
    saved = 0
    for f in request.FILES.getlist("photos")[:MAX_PHOTOS]:
        if f.size > MAX_PHOTO_BYTES:
            continue
        try:
            forms.ImageField().clean(f)  # Pillow verifies it really is an image
        except ValidationError:
            continue
        await VaultPhoto.objects.acreate(family=family, image=f)
        saved += 1
    return _back(token, "#boveda", f"?subidas={saved}")


def media(request, path):
    """Serve uploads with single-range support: iPhone won't play audio without 206 responses."""
    try:
        full = safe_join(settings.MEDIA_ROOT, path)
    except SuspiciousFileOperation:
        raise Http404
    if not os.path.isfile(full):
        raise Http404
    size = os.path.getsize(full)
    ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", request.headers.get("Range", ""))
    if not m or not (m[1] or m[2]):
        return FileResponse(open(full, "rb"), content_type=ctype, headers={"Accept-Ranges": "bytes"})
    start = int(m[1]) if m[1] else max(size - int(m[2]), 0)
    end = min(int(m[2]), size - 1) if m[1] and m[2] else size - 1
    if start > end:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
    with open(full, "rb") as f:
        f.seek(start)
        data = f.read(end - start + 1)
    return HttpResponse(
        data, status=206, content_type=ctype, headers={"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes"}
    )


async def calendar(request):
    event = await Event.objects.afirst()
    if event is None:
        return HttpResponse(status=404)
    return HttpResponse(
        event.ics(),
        content_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="fiesta.ics"'},
    )

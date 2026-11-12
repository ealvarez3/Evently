from urllib.parse import quote

from django.contrib import admin
from django.db.models import Sum
from django.urls import reverse
from django.utils.html import format_html

from .models import Event, Family, GrowthPhoto, ItineraryItem, SongSuggestion, VaultPhoto

admin.site.site_header = "Invitación · Administración"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    readonly_fields = ["resumen"]

    def has_add_permission(self, request):
        return not Event.objects.exists()  # one party only

    @admin.display(description="Confirmados")
    def resumen(self, obj):
        t = Family.objects.filter(status=Family.Status.YES).aggregate(a=Sum("adults"), b=Sum("boys"), g=Sum("girls"))
        pending = Family.objects.filter(status=Family.Status.PENDING).count()
        return f"{t['a'] or 0} adultos, {t['b'] or 0} niños, {t['g'] or 0} niñas · {pending} invitaciones sin responder"


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ["surname", "adults", "boys", "girls", "status", "responded_at", "enlace"]
    list_filter = ["status"]
    search_fields = ["surname"]
    readonly_fields = ["enlace"]

    def get_queryset(self, request):
        self._request = request  # needed to build absolute links in `enlace`
        return super().get_queryset(request)

    @admin.display(description="Enlace para compartir")
    def enlace(self, obj):
        if not obj.pk:
            return "Guarda para generar el enlace"
        url = self._request.build_absolute_uri(reverse("invitation", args=[obj.token]))
        text = quote(f"¡{obj.surname}! Esta es tu invitación a la fiesta: {url}")
        return format_html(
            '<a href="{0}" target="_blank">{0}</a> · <a href="https://wa.me/?text={1}" target="_blank">WhatsApp</a>',
            url,
            text,
        )


@admin.register(ItineraryItem)
class ItineraryAdmin(admin.ModelAdmin):
    list_display = ["time", "icon", "title", "description"]
    ordering = ["time"]


@admin.register(GrowthPhoto)
class GrowthPhotoAdmin(admin.ModelAdmin):
    list_display = ["__str__", "order"]
    list_editable = ["order"]
    ordering = ["order", "id"]


@admin.register(SongSuggestion)
class SongAdmin(admin.ModelAdmin):
    list_display = ["title", "artist", "family", "created"]


@admin.register(VaultPhoto)
class VaultPhotoAdmin(admin.ModelAdmin):
    list_display = ["miniatura", "family", "visible", "created"]
    list_editable = ["visible"]
    list_filter = ["visible"]

    @admin.display(description="Foto")
    def miniatura(self, obj):
        return format_html('<img src="{}" style="height:60px">', obj.image.url)

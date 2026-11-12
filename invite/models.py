import datetime
import secrets
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from PIL import Image, ImageOps


def shrink(f, size=1600):
    """Phone photos are huge: fix rotation, cap at 1600px, store as JPEG."""
    if not f or f._committed:
        return
    img = ImageOps.exif_transpose(Image.open(f))
    img.thumbnail((size, size))
    buf = BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=82)
    f.save(Path(f.name).stem + ".jpg", ContentFile(buf.getvalue()), save=False)


def _utc(dt):
    return dt.astimezone(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def _place(title, icon, name, address, lat, lng, when):
    ll, d = f"{lat},{lng}", 0.004
    return {
        "title": title,
        "icon": icon,
        "name": name,
        "address": address,
        "when": when,
        "google": "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": ll}),
        "waze": "https://waze.com/ul?" + urlencode({"ll": ll, "navigate": "yes"}),
        "apple": "https://maps.apple.com/?" + urlencode({"ll": ll, "q": name}),
        "embed": "https://www.openstreetmap.org/export/embed.html?"
        + urlencode(
            {"bbox": f"{float(lng) - d},{float(lat) - d},{float(lng) + d},{float(lat) + d}", "layer": "mapnik", "marker": ll}
        ),
    }


class Event(models.Model):
    child_name = models.CharField("nombre corto", max_length=60, default="Sebastián Isaí")
    child_full_name = models.CharField("nombre completo", max_length=120, default="Sebastián Isaí Velazquez Sanchez")
    age = models.PositiveSmallIntegerField("años que cumple", default=3)
    hero_character = models.ImageField("foto de Spidey (hero)", upload_to="hero/", blank=True)
    hero_child = models.ImageField("foto del festejado (hero)", upload_to="hero/", blank=True)
    start = models.DateTimeField("inicio")
    end = models.DateTimeField("fin")
    venue_name = models.CharField("lugar", max_length=120)
    address = models.CharField("dirección", max_length=255)
    latitude = models.DecimalField("latitud", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("longitud", max_digits=9, decimal_places=6)
    dress_code = models.TextField(
        "texto de vestimenta",
        default="Ven con una prenda de tu superhéroe favorito: una capa, un antifaz, una playera… "
        "¡el que tú quieras! No es obligatorio, pero la fiesta se pone más divertida.",
    )
    vault_opens_at = models.DateTimeField("la bóveda de fotos abre")
    cover_audio = models.FileField("voz de la portada (mp3)", upload_to="musica/", blank=True, help_text="Suena al tocar el botón; al terminar se abre la invitación")
    cover_photo = models.ImageField("foto mientras suena la voz", upload_to="hero/", blank=True, help_text="Si está vacío se queda el logo")
    cover_image = models.ImageField("logo de la portada", upload_to="hero/", blank=True, help_text="Negro sobre blanco o PNG transparente")
    church_name = models.CharField("iglesia", max_length=120, blank=True, help_text="Déjalo vacío si no hay ceremonia")
    church_address = models.CharField("dirección de la iglesia", max_length=255, blank=True)
    church_latitude = models.DecimalField("latitud de la iglesia", max_digits=9, decimal_places=6, null=True, blank=True)
    church_longitude = models.DecimalField("longitud de la iglesia", max_digits=9, decimal_places=6, null=True, blank=True)
    church_time = models.DateTimeField("hora de la ceremonia", null=True, blank=True)
    music = models.FileField("canción de fondo (mp3)", upload_to="musica/", blank=True)
    swing_image = models.ImageField(
        "imagen que se columpia", upload_to="hero/", blank=True, help_text="PNG con fondo transparente; si está vacío sale una arañita"
    )

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "evento"

    def __str__(self):
        return f"Fiesta de {self.child_name}"

    @property
    def title(self):
        return f"¡{self.child_name} cumple {self.age}!"

    @property
    def vault_open(self):
        return timezone.now() >= self.vault_opens_at

    @property
    def places(self):
        """Location cards, in the order the day happens: church (optional), then the party."""
        out = []
        if self.church_name and self.church_latitude is not None and self.church_longitude is not None:
            out.append(
                _place("Iglesia", "⛪", self.church_name, self.church_address, self.church_latitude, self.church_longitude, self.church_time)
            )
        out.append(_place("La fiesta", "🎉", self.venue_name, self.address, self.latitude, self.longitude, self.start))
        return out

    @property
    def google_calendar_url(self):
        return "https://calendar.google.com/calendar/render?" + urlencode(
            {
                "action": "TEMPLATE",
                "text": self.title,
                "dates": f"{_utc(self.start)}/{_utc(self.end)}",
                "location": f"{self.venue_name}, {self.address}",
            }
        )

    def ics(self):
        esc = lambda s: s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")
        return "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//Evently//ES",
                "BEGIN:VEVENT",
                f"UID:evently-{self.pk}@fiesta",
                f"DTSTAMP:{_utc(timezone.now())}",
                f"DTSTART:{_utc(self.start)}",
                f"DTEND:{_utc(self.end)}",
                f"SUMMARY:{esc(self.title)}",
                f"LOCATION:{esc(self.venue_name + ', ' + self.address)}",
                f"GEO:{self.latitude};{self.longitude}",
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ]
        )


def _token():
    return secrets.token_urlsafe(8)


class Family(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Sin responder"
        YES = "yes", "Asistirá"
        NO = "no", "No asistirá"

    surname = models.CharField("invitado", max_length=80, help_text="Tal como se mostrará: «Familia Pérez» o «Jesús Jiménez»")
    token = models.CharField(max_length=22, unique=True, default=_token, editable=False)
    adults = models.PositiveSmallIntegerField("adultos", default=2)
    boys = models.PositiveSmallIntegerField("niños", default=0)
    girls = models.PositiveSmallIntegerField("niñas", default=0)
    status = models.CharField("respuesta", max_length=8, choices=Status, default=Status.PENDING)
    responded_at = models.DateTimeField("respondió", null=True, blank=True)

    class Meta:
        verbose_name = "invitado"

    def __str__(self):
        return self.surname


class ItineraryItem(models.Model):
    icon = models.CharField("icono (emoji)", max_length=8, default="🎉")
    title = models.CharField("título", max_length=80)
    description = models.CharField("descripción", max_length=255, blank=True)
    time = models.TimeField("hora")

    class Meta:
        verbose_name = "actividad"
        verbose_name_plural = "itinerario"

    def __str__(self):
        return f"{self.time:%H:%M} {self.title}"


class GrowthPhoto(models.Model):
    image = models.ImageField("foto", upload_to="crecimiento/")
    caption = models.CharField("pie de foto", max_length=80, blank=True)
    order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        verbose_name = "foto de crecimiento"
        verbose_name_plural = "así he crecido"

    def __str__(self):
        return self.caption or self.image.name

    def save(self, *args, **kwargs):
        shrink(self.image)
        super().save(*args, **kwargs)


class SongSuggestion(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, verbose_name="invitado")
    title = models.CharField("canción", max_length=120)
    artist = models.CharField("artista", max_length=120, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "canción sugerida"
        verbose_name_plural = "canciones sugeridas"

    def __str__(self):
        return f"{self.title} — {self.artist}" if self.artist else self.title


class VaultPhoto(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE, verbose_name="invitado")
    image = models.ImageField("foto", upload_to="boveda/")
    visible = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "foto de la bóveda"
        verbose_name_plural = "bóveda de fotos"

    def __str__(self):
        return self.image.name

    def save(self, *args, **kwargs):
        shrink(self.image)
        super().save(*args, **kwargs)

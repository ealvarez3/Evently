from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Event, Family, VaultPhoto


def make_event(vault_delta):
    now = timezone.now()
    return Event.objects.create(
        start=now + timedelta(days=5),
        end=now + timedelta(days=5, hours=10),
        venue_name="Salón",
        address="Calle 1",
        latitude="19.432600",
        longitude="-99.133200",
        vault_opens_at=now + vault_delta,
    )


def png():
    buf = BytesIO()
    Image.new("RGB", (20, 20), "red").save(buf, "PNG")
    return SimpleUploadedFile("a.png", buf.getvalue(), content_type="image/png")


class InvitationTests(TestCase):
    def setUp(self):
        self.family = Family.objects.create(surname="Pérez", adults=2, boys=1)

    def test_page_and_rsvp(self):
        make_event(timedelta(days=6))
        r = self.client.get(reverse("invitation", args=[self.family.token]))
        self.assertContains(r, "Pérez")
        self.assertEqual(self.client.get(reverse("invitation", args=["nope"])).status_code, 404)
        self.client.post(reverse("rsvp", args=[self.family.token]), {"answer": "yes"})
        self.family.refresh_from_db()
        self.assertEqual(self.family.status, Family.Status.YES)
        self.assertIn("DTSTART", self.client.get(reverse("calendar")).content.decode())

    def test_church_card_and_media_range(self):
        import tempfile
        from pathlib import Path

        e = make_event(timedelta(days=6))
        self.assertEqual(len(e.places), 1)
        e.church_name, e.church_latitude, e.church_longitude = "Parroquia", "19.4", "-99.1"
        e.save()
        self.assertContains(self.client.get(reverse("home")), "Parroquia")
        d = tempfile.mkdtemp()
        Path(d, "a.mp3").write_bytes(b"0123456789")
        with override_settings(MEDIA_ROOT=d):
            r = self.client.get("/media/a.mp3", headers={"Range": "bytes=2-5"})
            self.assertEqual((r.status_code, r.content, r["Content-Range"]), (206, b"2345", "bytes 2-5/10"))
            self.assertEqual(self.client.get("/media/../manage.py").status_code, 404)

    def test_vault_locked_until_date(self):
        make_event(timedelta(days=6))
        r = self.client.post(reverse("vault_upload", args=[self.family.token]), {"photos": png()})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(VaultPhoto.objects.count(), 0)

    def test_vault_accepts_only_images(self):
        make_event(timedelta(days=-1))
        import tempfile

        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            bad = SimpleUploadedFile("x.jpg", b"not an image")
            self.client.post(reverse("vault_upload", args=[self.family.token]), {"photos": [png(), bad]})
        self.assertEqual(VaultPhoto.objects.count(), 1)

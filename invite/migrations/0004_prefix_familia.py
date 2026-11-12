from django.db import migrations
from django.db.models import Value
from django.db.models.functions import Concat


def prefix(apps, schema_editor):
    # the page used to add "Familia" itself; keep existing guests reading the same
    Family = apps.get_model("invite", "Family")
    Family.objects.exclude(surname__istartswith="familia").update(surname=Concat(Value("Familia "), "surname"))


class Migration(migrations.Migration):
    dependencies = [("invite", "0003_alter_family_options_event_cover_image_and_more")]
    operations = [migrations.RunPython(prefix, migrations.RunPython.noop)]

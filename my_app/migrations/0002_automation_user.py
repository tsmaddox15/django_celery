"""Creates the admin user the example browser automations log in as, using the
AUTOMATION_SITE_* settings (`automation` / `automation` by default)."""

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_automation_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    if not User.objects.filter(username=settings.AUTOMATION_SITE_USERNAME).exists():
        User.objects.create(
            username=settings.AUTOMATION_SITE_USERNAME,
            password=make_password(settings.AUTOMATION_SITE_PASSWORD),
            is_staff=True,
            is_superuser=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('my_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_automation_user, migrations.RunPython.noop),
    ]

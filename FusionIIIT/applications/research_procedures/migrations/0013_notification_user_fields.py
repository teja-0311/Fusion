# Generated migration for Notification model user fields (UC-015)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0012_project_uc004_uc005_uc012_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # sender column already exists from partial previous migration run
        # This is now a no-op migration
    ]


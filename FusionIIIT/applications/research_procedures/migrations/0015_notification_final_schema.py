# Final schema fix - handles partial migration state

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0013_notification_user_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Remove old recipient CharField if it exists
        # (It may have already been removed, so we try to remove it)
        migrations.RemoveField(
            model_name='notification',
            name='recipient',
        ),
        
        # Step 2: Add recipient as ForeignKey
        migrations.AddField(
            model_name='notification',
            name='recipient',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications_received',
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]

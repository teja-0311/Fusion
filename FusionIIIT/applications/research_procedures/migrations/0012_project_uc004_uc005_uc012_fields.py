# Generated migration for UC-004, UC-005, UC-012 Project fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0011_create_rspc_test_users'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # UC-004: Update tracking fields
        migrations.AddField(
            model_name='project',
            name='allow_updates_after_approval',
            field=models.BooleanField(
                default=False,
                help_text='BR-011: Allow updates post-approval'
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='last_updated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects_updated',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='last_updated_date',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # UC-005: Cancellation fields
        migrations.AddField(
            model_name='project',
            name='cancellation_reason',
            field=models.TextField(blank=True, help_text='Reason for project cancellation'),
        ),
        migrations.AddField(
            model_name='project',
            name='cancelled_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects_cancelled',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='cancelled_date',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # UC-012: HOD vetting fields
        migrations.AddField(
            model_name='project',
            name='hod_vetting_status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')],
                default='PENDING',
                help_text='BR-RSPC-10: HOD vetting status',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='hod_vetting_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

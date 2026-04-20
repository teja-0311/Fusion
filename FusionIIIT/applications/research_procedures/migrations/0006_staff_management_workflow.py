# Generated migration for Staff Management Workflow (UC-007, UC-008, UC-026, UC-027)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('globals', '0001_initial'),
        ('research_procedures', '0005_expenditure_approval_system'),
    ]

    operations = [
        # Enhance CommitteeVerdict model with conflict of interest tracking
        migrations.AddField(
            model_name='committeeverdict',
            name='has_conflict_of_interest',
            field=models.BooleanField(default=False, help_text='BR-RSPC-15: Conflict of interest'),
        ),
        migrations.AddField(
            model_name='committeeverdict',
            name='conflict_reason',
            field=models.TextField(blank=True, help_text='Reason for conflict if applicable'),
        ),
        migrations.AddField(
            model_name='committeeverdict',
            name='submitted_date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='committeeverdict',
            name='decision',
            field=models.CharField(blank=True, choices=[('APPROVE', 'Approve'), ('REJECT', 'Reject'), ('ABSTAIN', 'Abstain')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='committeeverdict',
            name='committee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verdicts', to='research_procedures.committee'),
        ),
        migrations.AlterField(
            model_name='committeeverdict',
            name='member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verdicts', to='globals.extrainfo'),
        ),
        
        # Enhance Staff model with additional fields
        migrations.AddField(
            model_name='staff',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='staff',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='staff',
            name='modified_date',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='staff',
            name='no_of_positions',
            field=models.IntegerField(default=1, help_text='Number of positions to fill'),
        ),
        migrations.AddField(
            model_name='staff',
            name='qualification',
            field=models.TextField(blank=True, help_text='Required qualifications'),
        ),
        migrations.AddField(
            model_name='staff',
            name='experience',
            field=models.IntegerField(default=0, help_text='Required years of experience'),
        ),
        migrations.AddField(
            model_name='staff',
            name='approval_chain',
            field=models.JSONField(default=dict, help_text='Tracks approval history at each stage'),
        ),
        
        # Update Staff meta options
        migrations.AlterModelOptions(
            name='staff',
            options={
                'ordering': ['-created_date'],
                'verbose_name': 'Staff',
                'verbose_name_plural': 'Staff',
            },
        ),
        
        # Add indexes to Staff model
        migrations.AddIndex(
            model_name='staff',
            index=models.Index(fields=['pid', 'approval_status'], name='staff_pid_approval_idx'),
        ),
        migrations.AddIndex(
            model_name='staff',
            index=models.Index(fields=['approval_status'], name='staff_approval_status_idx'),
        ),
        migrations.AddIndex(
            model_name='staff',
            index=models.Index(fields=['created_by'], name='staff_created_by_idx'),
        ),
        
        # Create new CommitteeMember model (UC-026, BR-RSPC-12)
        migrations.CreateModel(
            name='CommitteeMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('appointed_date', models.DateTimeField(auto_now_add=True)),
                ('is_pi_eligible', models.BooleanField(default=False, help_text='BR-RSPC-12: Must be Professor/Assoc/Asst Prof')),
                ('designation', models.CharField(blank=True, max_length=100)),
                ('department', models.CharField(blank=True, max_length=100)),
                ('committee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='committee_members', to='research_procedures.committee')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='committee_appointments', to='globals.extrainfo')),
            ],
            options={
                'verbose_name': 'Committee Member',
                'verbose_name_plural': 'Committee Members',
                'db_table': 'rspc_committee_member',
            },
        ),
        migrations.AddConstraint(
            model_name='committeemember',
            constraint=models.UniqueConstraint(fields=['committee', 'member'], name='unique_committee_member'),
        ),
    ]

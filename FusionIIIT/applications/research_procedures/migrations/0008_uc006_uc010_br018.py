# Generated migration for UC-006, UC-010, and BR-018 implementation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0007_research_group_timestamps'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add BR-018 fields to existing models
        migrations.AddField(
            model_name='project',
            name='approval_deadline',
            field=models.DateTimeField(blank=True, help_text='Approval deadline (10 days from submission)', null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='approval_status_escalated',
            field=models.BooleanField(default=False, help_text='BR-018: Has approval been escalated?'),
        ),
        migrations.AddField(
            model_name='project',
            name='escalation_date',
            field=models.DateTimeField(blank=True, help_text='When approval was escalated', null=True),
        ),
        
        # Add BR-018 fields to Expenditure model
        migrations.AddField(
            model_name='expenditure',
            name='approval_deadline',
            field=models.DateTimeField(blank=True, help_text='Deadline based on amount tier', null=True),
        ),
        migrations.AddField(
            model_name='expenditure',
            name='approval_status_escalated',
            field=models.BooleanField(default=False, help_text='BR-018: Has approval been escalated?'),
        ),
        migrations.AddField(
            model_name='expenditure',
            name='escalation_date',
            field=models.DateTimeField(blank=True, help_text='When approval was escalated', null=True),
        ),
        
        # Add BR-018 fields to Staff model
        migrations.AddField(
            model_name='staff',
            name='approval_deadline',
            field=models.DateTimeField(blank=True, help_text='Approval deadline (7 days from submission)', null=True),
        ),
        migrations.AddField(
            model_name='staff',
            name='approval_status_escalated',
            field=models.BooleanField(default=False, help_text='BR-018: Has approval been escalated?'),
        ),
        migrations.AddField(
            model_name='staff',
            name='escalation_date',
            field=models.DateTimeField(blank=True, help_text='When approval was escalated', null=True),
        ),
        
        # Create ProgressReport model (UC-006)
        migrations.CreateModel(
            name='ProgressReport',
            fields=[
                ('prid', models.AutoField(primary_key=True, serialize=False)),
                ('report_period', models.CharField(choices=[('QUARTERLY', 'Quarterly'), ('HALF_YEARLY', 'Half Yearly'), ('ANNUAL', 'Annual'), ('FINAL', 'Final')], max_length=20)),
                ('report_content', models.TextField(help_text='Project progress summary')),
                ('challenges_faced', models.TextField(help_text='Key challenges encountered')),
                ('milestones_achieved', models.TextField(help_text='Milestones completed in this period')),
                ('publications_filed', models.IntegerField(default=0, help_text='Number of publications')),
                ('recommendations', models.TextField(blank=True, help_text='Future recommendations')),
                ('attachments', models.FileField(blank=True, null=True, upload_to='rspc/reports/progress/')),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'), ('REVIEWED', 'Reviewed'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='DRAFT', max_length=20)),
                ('reviewer_comments', models.TextField(blank=True, help_text='Comments from RSPC Admin/Director')),
                ('submitted_date', models.DateTimeField(blank=True, null=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_reports', to='research_procedures.project')),
                ('submitted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='progress_reports_submitted', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Progress Report',
                'verbose_name_plural': 'Progress Reports',
                'db_table': 'rspc_progress_report',
                'ordering': ['-created_date'],
                'unique_together': {('project', 'report_period')},
            },
        ),
        
        # Create ProjectClosure model (UC-010)
        migrations.CreateModel(
            name='ProjectClosure',
            fields=[
                ('closure_id', models.AutoField(primary_key=True, serialize=False)),
                ('final_report', models.TextField(help_text='Final project report')),
                ('deliverables_summary', models.TextField(help_text='Summary of deliverables')),
                ('challenges_summary', models.TextField(help_text='Summary of challenges')),
                ('lessons_learned', models.TextField(help_text='Lessons learned and recommendations')),
                ('publications_generated', models.IntegerField(default=0)),
                ('patents_filed', models.IntegerField(default=0)),
                ('utilization_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('final_settlement_document', models.FileField(blank=True, null=True, upload_to='rspc/closure/settlement/')),
                ('outstanding_items', models.TextField(blank=True, help_text='Any outstanding items pending')),
                ('status', models.CharField(choices=[('SUBMITTED', 'Submitted'), ('VERIFIED', 'Verified'), ('SETTLED', 'Settled'), ('CLOSED', 'Closed')], default='SUBMITTED', max_length=20)),
                ('closure_date', models.DateTimeField(auto_now_add=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('closed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_closures', to=settings.AUTH_USER_MODEL)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='closure_report', to='research_procedures.project')),
            ],
            options={
                'verbose_name': 'Project Closure',
                'verbose_name_plural': 'Project Closures',
                'db_table': 'rspc_project_closure',
                'ordering': ['-created_date'],
            },
        ),
        
        # Create ApprovalSLA model (BR-018)
        migrations.CreateModel(
            name='ApprovalSLA',
            fields=[
                ('sla_id', models.AutoField(primary_key=True, serialize=False)),
                ('entity_type', models.CharField(choices=[('expenditure', 'Expenditure'), ('project', 'Project'), ('staff', 'Staff'), ('progress_report', 'Progress Report'), ('project_closure', 'Project Closure')], max_length=20)),
                ('entity_id', models.CharField(max_length=100)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('deadline', models.DateTimeField(help_text='Approval deadline based on BR-018')),
                ('escalation_level', models.IntegerField(choices=[(1, 'Level 1'), (2, 'Level 2'), (3, 'Level 3')], default=1)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('ESCALATED', 'Escalated'), ('TIMEOUT', 'Timeout')], default='PENDING', max_length=20)),
                ('timeout_notified', models.BooleanField(default=False, help_text='Has timeout notification been sent?')),
                ('escalation_date', models.DateTimeField(blank=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('current_approver', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approvals_pending', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Approval SLA',
                'verbose_name_plural': 'Approval SLAs',
                'db_table': 'rspc_approval_sla',
                'ordering': ['deadline'],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='progressreport',
            index=models.Index(fields=['project', 'status'], name='rspc_prog_p_s_idx'),
        ),
        migrations.AddIndex(
            model_name='progressreport',
            index=models.Index(fields=['submitted_by', '-created_date'], name='rspc_prog_sb_idx'),
        ),
        migrations.AddIndex(
            model_name='progressreport',
            index=models.Index(fields=['status'], name='rspc_prog_s_idx'),
        ),
        migrations.AddIndex(
            model_name='projectclosure',
            index=models.Index(fields=['project', 'status'], name='rspc_close_p_s_idx'),
        ),
        migrations.AddIndex(
            model_name='projectclosure',
            index=models.Index(fields=['status'], name='rspc_close_s_idx'),
        ),
        migrations.AddIndex(
            model_name='approvalsla',
            index=models.Index(fields=['entity_type', 'entity_id'], name='rspc_sla_e_idx'),
        ),
        migrations.AddIndex(
            model_name='approvalsla',
            index=models.Index(fields=['status', 'deadline'], name='rspc_sla_sd_idx'),
        ),
        migrations.AddIndex(
            model_name='approvalsla',
            index=models.Index(fields=['current_approver', 'status'], name='rspc_sla_ca_idx'),
        ),
    ]

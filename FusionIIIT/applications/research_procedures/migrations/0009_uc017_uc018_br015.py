# Generated migration for UC-017, UC-018, BR-015

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0008_uc006_uc010_br018'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add new status choices
        migrations.CreateModel(
            name='StipendDisbursement',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('month', models.DateField(help_text='Start of month for stipend')),
                ('stipend_amount', models.DecimalField(decimal_places=2, help_text='BR-009: Within approved limits', max_digits=15)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('DISBURSED', 'Disbursed'), ('FAILED', 'Failed'), ('HOLD', 'On Hold')], default='PENDING', max_length=20)),
                ('disbursement_date', models.DateTimeField(blank=True, null=True)),
                ('payment_method', models.CharField(blank=True, choices=[('BANK', 'Bank Transfer'), ('CHECK', 'Check'), ('CASH', 'Cash')], max_length=20, null=True)),
                ('payment_reference', models.CharField(blank=True, help_text='Bank ref/check no', max_length=100)),
                ('remarks', models.TextField(blank=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staff_stipends', to='research_procedures.project')),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stipend_disbursements', to='research_procedures.staff')),
            ],
            options={
                'verbose_name': 'Stipend Disbursement',
                'verbose_name_plural': 'Stipend Disbursements',
                'db_table': 'rspc_stipend_disbursement',
                'ordering': ['-month'],
            },
        ),
        migrations.CreateModel(
            name='StipendBatch',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('batch_date', models.DateField(auto_now_add=True)),
                ('month', models.DateField(help_text='Month of stipend allocation')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, help_text='Auto-calculated', max_digits=15)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('DISBURSED', 'Disbursed'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('disbursement_count', models.IntegerField(default=0)),
                ('approval_date', models.DateTimeField(blank=True, null=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_stipend_batches', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stipend_batches', to='research_procedures.project')),
            ],
            options={
                'verbose_name': 'Stipend Batch',
                'verbose_name_plural': 'Stipend Batches',
                'db_table': 'rspc_stipend_batch',
                'ordering': ['-month'],
            },
        ),
        migrations.CreateModel(
            name='ComplianceReport',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('report_date', models.DateField(auto_now_add=True)),
                ('report_type', models.CharField(choices=[('BUDGET', 'Budget Compliance'), ('EXPENDITURE', 'Expenditure Compliance'), ('STAFF', 'Staff Compliance'), ('PROJECT', 'Project Compliance'), ('FULL', 'Full Compliance')], max_length=20)),
                ('period_start', models.DateField(help_text='Report period start')),
                ('period_end', models.DateField(help_text='Report period end')),
                ('status', models.CharField(choices=[('GENERATED', 'Generated'), ('REVIEWED', 'Reviewed'), ('APPROVED', 'Approved'), ('PUBLISHED', 'Published')], default='GENERATED', max_length=20)),
                ('total_items_checked', models.IntegerField(default=0)),
                ('compliant_items', models.IntegerField(default=0)),
                ('non_compliant_items', models.IntegerField(default=0)),
                ('compliance_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('report_content', models.JSONField(default=dict, help_text='Structured compliance data')),
                ('export_formats', models.JSONField(default=dict, help_text='PDF/Excel file paths')),
                ('notes', models.TextField(blank=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('generated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_compliance_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Compliance Report',
                'verbose_name_plural': 'Compliance Reports',
                'db_table': 'rspc_compliance_report',
                'ordering': ['-report_date'],
            },
        ),
        # Add settlement fields to ProjectClosure
        migrations.AddField(
            model_name='projectclosure',
            name='settlement_amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Final settlement amount to be released', max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='projectclosure',
            name='held_amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Amount held if any', max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='projectclosure',
            name='refund_amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Unused funds to be refunded', max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='projectclosure',
            name='penalty_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Penalties for timeline violations', max_digits=15),
        ),
        migrations.AddField(
            model_name='projectclosure',
            name='settlement_calculated',
            field=models.BooleanField(default=False, help_text='BR-015: Has settlement been calculated?'),
        ),
        migrations.AddField(
            model_name='projectclosure',
            name='settlement_approved',
            field=models.BooleanField(default=False, help_text='BR-015: Has settlement been approved by Director?'),
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='stipenddisbursement',
            index=models.Index(fields=['project', 'month'], name='rspc_stipe_project_idx'),
        ),
        migrations.AddIndex(
            model_name='stipenddisbursement',
            index=models.Index(fields=['staff', '-month'], name='rspc_stipe_staff_idx'),
        ),
        migrations.AddIndex(
            model_name='stipenddisbursement',
            index=models.Index(fields=['status'], name='rspc_stipe_status_idx'),
        ),
        migrations.AddIndex(
            model_name='stipendbatch',
            index=models.Index(fields=['project', 'month'], name='rspc_batch_project_idx'),
        ),
        migrations.AddIndex(
            model_name='stipendbatch',
            index=models.Index(fields=['status'], name='rspc_batch_status_idx'),
        ),
        migrations.AddIndex(
            model_name='compliancereport',
            index=models.Index(fields=['report_type', '-report_date'], name='rspc_comp_type_idx'),
        ),
        migrations.AddIndex(
            model_name='compliancereport',
            index=models.Index(fields=['status'], name='rspc_comp_status_idx'),
        ),
        # Add unique constraints
        migrations.AlterUniqueTogether(
            name='stipenddisbursement',
            unique_together={('staff', 'project', 'month')},
        ),
        migrations.AlterUniqueTogether(
            name='stipendbatch',
            unique_together={('project', 'month')},
        ),
    ]

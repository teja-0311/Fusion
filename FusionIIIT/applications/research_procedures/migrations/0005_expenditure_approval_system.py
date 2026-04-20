"""
RSPC Expenditure Approval System - Database Migration
UC-012, UC-013, BR-RSPC-13 Implementation

Creates:
- Expenditure model with 3-tier approval chain
- ExpenditureApprovalHistory model for audit trail
- Status and role choice fields
"""

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0004_budget_models'),
    ]

    operations = [
        # Add new status and role fields
        migrations.AddField(
            model_name='expenditure',
            name='current_stage',
            field=models.IntegerField(
                choices=[(0, 'PI Approval'), (1, 'HOD Approval'), (2, 'RSPC Admin Approval')],
                default=0
            ),
        ),
        
        migrations.AddField(
            model_name='expenditure',
            name='approval_chain',
            field=models.JSONField(
                default=dict,
                help_text='Tracks approval history: {stage: {approver, approved_at, comments}}'
            ),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('PI_APPROVED', 'PI Approved'),
                    ('HOD_APPROVED', 'HOD Approved'),
                    ('RSPC_APPROVED', 'RSPC Admin Approved'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected')
                ],
                default='PENDING',
                max_length=20
            ),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='category',
            field=models.CharField(
                choices=[
                    ('MANPOWER', 'Manpower'),
                    ('EQUIPMENT', 'Equipment'),
                    ('CONSUMABLES', 'Consumables'),
                    ('TRAVEL', 'Travel'),
                    ('CONTINGENCY', 'Contingency'),
                    ('OVERHEAD', 'Overhead'),
                    ('OTHER', 'Other')
                ],
                max_length=20
            ),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=15,
                validators=[django.core.validators.MinValueValidator(0)]
            ),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='purpose',
            field=models.TextField(
                validators=[django.core.validators.MinLengthValidator(20)]
            ),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='requested_by',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='expenditures_created',
                to='globals.extrainfo'
            ),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='requested_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='current_approver',
            field=models.CharField(
                blank=True,
                choices=[('PI', 'Principal Investigator'), ('HOD', 'Head of Department'), ('RSPC', 'RSPC Administrator')],
                default='PI',
                max_length=10,
                null=True
            ),
        ),
        
        migrations.AddField(
            model_name='expenditure',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        
        migrations.AddField(
            model_name='expenditure',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        
        migrations.AlterField(
            model_name='expenditure',
            name='project',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='expenditures',
                to='research_procedures.project'
            ),
        ),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='expenditure',
            index=models.Index(fields=['project', 'status'], name='expenditure_project_status_idx'),
        ),
        
        migrations.AddIndex(
            model_name='expenditure',
            index=models.Index(fields=['current_approver', 'status'], name='expenditure_approver_status_idx'),
        ),
        
        migrations.AddIndex(
            model_name='expenditure',
            index=models.Index(fields=['amount', 'status'], name='expenditure_amount_status_idx'),
        ),
        
        # Create ExpenditureApprovalHistory model
        migrations.CreateModel(
            name='ExpenditureApprovalHistory',
            fields=[
                ('ahid', models.AutoField(primary_key=True, serialize=False)),
                ('approver_role', models.CharField(
                    choices=[('PI', 'Principal Investigator'), ('HOD', 'Head of Department'), ('RSPC', 'RSPC Administrator')],
                    max_length=10
                )),
                ('action', models.CharField(
                    choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected')],
                    max_length=20
                )),
                ('comments', models.TextField(blank=True)),
                ('approved_at', models.DateTimeField(auto_now_add=True)),
                ('approver', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_expenditures',
                    to='globals.extrainfo'
                )),
                ('expenditure', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='approval_history',
                    to='research_procedures.expenditure'
                )),
            ],
            options={
                'verbose_name': 'Expenditure Approval History',
                'verbose_name_plural': 'Expenditure Approval Histories',
                'db_table': 'rspc_expenditure_approval_history',
                'ordering': ['-approved_at'],
            },
        ),
    ]

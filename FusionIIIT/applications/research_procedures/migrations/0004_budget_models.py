from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0003_rspc_domain_models'),
    ]

    operations = [
        # ── Enhanced Budget Model with utilization tracking ──────────────────
        migrations.AlterField(
            model_name='budget',
            name='bid',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.RemoveField(
            model_name='budget',
            name='pid',
        ),
        migrations.AddField(
            model_name='budget',
            name='project',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='budget',
                default=1,
                to='research_procedures.project'
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='budget',
            name='manpower',
            field=models.JSONField(default=dict, help_text='Year-wise manpower budget'),
        ),
        migrations.AlterField(
            model_name='budget',
            name='travel',
            field=models.JSONField(default=dict, help_text='Year-wise travel budget'),
        ),
        migrations.AlterField(
            model_name='budget',
            name='consumables',
            field=models.JSONField(default=dict, help_text='Year-wise consumables budget'),
        ),
        migrations.RenameField(
            model_name='budget',
            old_name='equipments',
            new_name='equipment',
        ),
        migrations.AlterField(
            model_name='budget',
            name='equipment',
            field=models.JSONField(default=dict, help_text='Year-wise equipment budget'),
        ),
        migrations.AlterField(
            model_name='budget',
            name='contingency',
            field=models.JSONField(default=dict, help_text='Year-wise contingency budget'),
        ),
        # Note: overhead field type conversion from DecimalField to JSONField
        # handled by RemoveField + AddField due to type incompatibility
        migrations.RemoveField(
            model_name='budget',
            name='overhead',
        ),
        migrations.AddField(
            model_name='budget',
            name='overhead',
            field=models.JSONField(default=dict, help_text='Year-wise overhead budget/percentage'),
        ),
        migrations.RemoveField(
            model_name='budget',
            name='total_budget',
        ),
        migrations.AddField(
            model_name='budget',
            name='total_sanctioned',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
        migrations.AddField(
            model_name='budget',
            name='utilized_amounts',
            field=models.JSONField(
                default=dict,
                help_text='Per-category utilization tracking with timestamps'
            ),
        ),
        migrations.AddField(
            model_name='budget',
            name='last_modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='budget',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='budget',
            name='modified_by',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),

        # ── BudgetReallocation Model ────────────────────────────────────────
        migrations.CreateModel(
            name='BudgetReallocation',
            fields=[
                ('rbid', models.AutoField(primary_key=True, serialize=False)),
                ('from_category', models.CharField(
                    choices=[
                        ('MANPOWER', 'Manpower'),
                        ('EQUIPMENT', 'Equipment'),
                        ('CONSUMABLES', 'Consumables'),
                        ('TRAVEL', 'Travel'),
                        ('CONTINGENCY', 'Contingency'),
                        ('OVERHEAD', 'Overhead'),
                        ('OTHER', 'Other'),
                    ],
                    max_length=50
                )),
                ('to_category', models.CharField(
                    choices=[
                        ('MANPOWER', 'Manpower'),
                        ('EQUIPMENT', 'Equipment'),
                        ('CONSUMABLES', 'Consumables'),
                        ('TRAVEL', 'Travel'),
                        ('CONTINGENCY', 'Contingency'),
                        ('OVERHEAD', 'Overhead'),
                        ('OTHER', 'Other'),
                    ],
                    max_length=50
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('financial_year', models.CharField(help_text='e.g., 2023-24', max_length=10)),
                ('justification', models.TextField()),
                ('requires_approval', models.BooleanField(
                    default=False,
                    help_text='True if reallocation exceeds 20% limit (BR-RSPC-08)'
                )),
                ('approval_status', models.CharField(
                    choices=[
                        ('REQUESTED', 'Requested'),
                        ('APPROVED', 'Approved'),
                        ('REJECTED', 'Rejected'),
                        ('IMPLEMENTED', 'Implemented'),
                    ],
                    default='REQUESTED',
                    max_length=20
                )),
                ('approved_by', models.CharField(blank=True, max_length=150, null=True)),
                ('approval_comments', models.TextField(blank=True, null=True)),
                ('requested_by', models.CharField(max_length=150)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('implemented_at', models.DateTimeField(blank=True, null=True)),
                ('budget', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reallocations',
                    to='research_procedures.budget'
                )),
            ],
            options={
                'verbose_name': 'Budget Reallocation',
                'verbose_name_plural': 'Budget Reallocations',
                'db_table': 'rspc_budget_reallocation',
            },
        ),

        # ── BudgetModificationHistory Model ────────────────────────────────
        migrations.CreateModel(
            name='BudgetModificationHistory',
            fields=[
                ('hmid', models.AutoField(primary_key=True, serialize=False)),
                ('modification_type', models.CharField(
                    choices=[
                        ('INITIAL', 'Initial Budget'),
                        ('REALLOCATION', 'Reallocation'),
                        ('UTILIZATION_UPDATE', 'Utilization Update'),
                        ('SANCTION_UPDATE', 'Sanction Amount Update'),
                    ],
                    max_length=50
                )),
                ('category', models.CharField(
                    blank=True,
                    choices=[
                        ('MANPOWER', 'Manpower'),
                        ('EQUIPMENT', 'Equipment'),
                        ('CONSUMABLES', 'Consumables'),
                        ('TRAVEL', 'Travel'),
                        ('CONTINGENCY', 'Contingency'),
                        ('OVERHEAD', 'Overhead'),
                        ('OTHER', 'Other'),
                    ],
                    max_length=50,
                    null=True
                )),
                ('old_value', models.JSONField(blank=True, null=True)),
                ('new_value', models.JSONField(blank=True, null=True)),
                ('change_amount', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=15,
                    null=True
                )),
                ('reason', models.TextField()),
                ('modified_by', models.CharField(max_length=150)),
                ('modified_at', models.DateTimeField(auto_now_add=True)),
                ('budget', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='modification_history',
                    to='research_procedures.budget'
                )),
                ('related_reallocation', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='research_procedures.budgetreallocation'
                )),
            ],
            options={
                'verbose_name': 'Budget Modification History',
                'verbose_name_plural': 'Budget Modification Histories',
                'db_table': 'rspc_budget_modification_history',
                'ordering': ['-modified_at'],
            },
        ),

        # ── Update Budget Meta ordering ─────────────────────────────────────
        migrations.AlterModelOptions(
            name='budget',
            options={
                'verbose_name': 'Budget',
                'verbose_name_plural': 'Budgets',
            },
        ),
    ]

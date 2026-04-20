from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0001_initial'),
    ]

    operations = [
        # Project (db_table = 'projects')
        migrations.CreateModel(
            name='Project',
            fields=[
                ('pid', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, unique=True)),
                ('pi_id', models.CharField(max_length=100)),
                ('pi_name', models.CharField(max_length=200)),
                ('access', models.CharField(
                    choices=[('Co', 'Co-PI can modify'), ('noCo', 'Only PI can modify')],
                    default='noCo', max_length=10)),
                ('type', models.CharField(max_length=50)),
                ('dept', models.CharField(max_length=100)),
                ('category', models.CharField(max_length=50)),
                ('sponsored_agency', models.CharField(max_length=200)),
                ('scheme', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('duration', models.IntegerField(validators=[
                    django.core.validators.MinValueValidator(6),
                    django.core.validators.MaxValueValidator(60)])),
                ('submission_date', models.DateTimeField()),
                ('total_budget', models.DecimalField(decimal_places=2, max_digits=15)),
                ('sanction_date', models.DateTimeField(blank=True, null=True)),
                ('sanctioned_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('initial_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('file', models.FileField(blank=True, null=True, upload_to='rspc/projects/')),
                ('registration_form', models.FileField(blank=True, null=True, upload_to='rspc/registrations/')),
                ('status', models.CharField(default='PROPOSED', max_length=50)),
                ('financial_outlay_status', models.IntegerField(default=0)),
                ('end_report', models.FileField(blank=True, null=True, upload_to='rspc/closure/')),
                ('end_approval', models.BooleanField(default=False)),
                ('years', models.IntegerField(default=1)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('file_id', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Project',
                'verbose_name_plural': 'Projects',
                'db_table': 'projects',
            },
        ),

        # Budget (db_table = 'budget')
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('bid', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.OneToOneField(
                    db_column='pid', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('manpower', models.JSONField(default=dict)),
                ('travel', models.JSONField(default=dict)),
                ('contingency', models.JSONField(default=dict)),
                ('consumables', models.JSONField(default=dict)),
                ('equipments', models.JSONField(default=dict)),
                ('overhead', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('total_budget', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('current_funds', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
            ],
            options={
                'verbose_name': 'Budget',
                'verbose_name_plural': 'Budgets',
                'db_table': 'budget',
            },
        ),

        # Staff (db_table = 'staff')
        migrations.CreateModel(
            name='Staff',
            fields=[
                ('sid', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.ForeignKey(
                    db_column='pid', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('person', models.CharField(max_length=200)),
                ('uname', models.CharField(max_length=100)),
                ('biodata_number', models.CharField(max_length=50)),
                ('start_date', models.DateTimeField()),
                ('duration', models.IntegerField()),
                ('eligibility', models.TextField()),
                ('type', models.CharField(max_length=50)),
                ('salary', models.DecimalField(decimal_places=2, max_digits=10)),
                ('has_funds', models.BooleanField(default=False)),
                ('post_on_website', models.BooleanField(default=False)),
                ('submission_date', models.DateTimeField(blank=True, null=True)),
                ('interview_date', models.DateTimeField(blank=True, null=True)),
                ('test_date', models.DateTimeField(blank=True, null=True)),
                ('test_mode', models.CharField(blank=True, max_length=50)),
                ('interview_place', models.CharField(blank=True, max_length=200)),
                ('selection_committee', models.JSONField(default=list)),
                ('candidates_applied', models.IntegerField(default=0)),
                ('candidates_called', models.IntegerField(default=0)),
                ('candidates_interviewed', models.IntegerField(default=0)),
                ('final_selection', models.JSONField(default=list)),
                ('waiting_list', models.JSONField(default=list)),
                ('biodata_final', models.JSONField(default=list)),
                ('biodata_waiting', models.JSONField(default=list)),
                ('ad_file', models.FileField(blank=True, null=True, upload_to='rspc/staff/ad/')),
                ('comparative_file', models.FileField(blank=True, null=True, upload_to='rspc/staff/comparative/')),
                ('approval', models.JSONField(default=dict)),
                ('gave_verdict', models.JSONField(default=dict)),
                ('current_approver', models.CharField(blank=True, max_length=100)),
                ('joining_report', models.FileField(blank=True, null=True, upload_to='rspc/staff/joining/')),
                ('doc_approval', models.BooleanField(default=False)),
                ('salary_per_month', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('id_card', models.FileField(blank=True, null=True, upload_to='rspc/staff/id_cards/')),
                ('approval_status', models.CharField(default='DRAFT', max_length=50)),
            ],
            options={
                'verbose_name': 'Staff',
                'verbose_name_plural': 'Staff',
                'db_table': 'staff',
            },
        ),

        # StaffPosition (db_table = 'staff_positions')
        migrations.CreateModel(
            name='StaffPosition',
            fields=[
                ('spid', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.OneToOneField(
                    db_column='pid', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('positions', models.JSONField(default=dict)),
                ('incumbents', models.JSONField(default=dict)),
                ('vacancy', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Staff Position',
                'verbose_name_plural': 'Staff Positions',
                'db_table': 'staff_positions',
            },
        ),

        # ProjectAccess / co_pis (db_table = 'co_pis')
        migrations.CreateModel(
            name='ProjectAccess',
            fields=[
                ('aid', models.AutoField(primary_key=True, serialize=False)),
                ('pid', models.ForeignKey(
                    db_column='pid', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('type', models.CharField(max_length=50)),
                ('copi_id', models.CharField(max_length=100)),
                ('affiliation', models.CharField(blank=True, max_length=200)),
                ('name', models.CharField(blank=True, max_length=200)),
            ],
            options={
                'verbose_name': 'Project Access',
                'verbose_name_plural': 'Project Accesses',
                'db_table': 'co_pis',
            },
        ),
        migrations.AlterUniqueTogether(
            name='projectaccess',
            unique_together={('pid', 'copi_id')},
        ),

        # CoPI (db_table = 'rspc_copi')
        migrations.CreateModel(
            name='CoPI',
            fields=[
                ('copi_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('type', models.CharField(max_length=50)),
                ('affiliation', models.CharField(blank=True, max_length=200)),
                ('username', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(blank=True)),
            ],
            options={
                'verbose_name': 'Co-Investigator',
                'verbose_name_plural': 'Co-Investigators',
                'db_table': 'rspc_copi',
            },
        ),

        # FinancialOutlay (db_table = 'financial_outlay')
        migrations.CreateModel(
            name='FinancialOutlay',
            fields=[
                ('financial_outlay_id', models.AutoField(primary_key=True, serialize=False)),
                ('project', models.ForeignKey(
                    db_column='project_id', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('category', models.CharField(max_length=100)),
                ('sub_category', models.CharField(max_length=100)),
                ('year', models.IntegerField()),
                ('allotted_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('utilized_amount', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
            ],
            options={
                'verbose_name': 'Financial Outlay',
                'verbose_name_plural': 'Financial Outlays',
                'db_table': 'financial_outlay',
            },
        ),
        migrations.AlterUniqueTogether(
            name='financialoutlay',
            unique_together={('project', 'category', 'sub_category', 'year')},
        ),

        # StaffAllocation (db_table = 'staff_allocations')
        migrations.CreateModel(
            name='StaffAllocation',
            fields=[
                ('allocation_id', models.AutoField(primary_key=True, serialize=False)),
                ('project', models.ForeignKey(
                    db_column='project_id', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('staff_id', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=200)),
                ('qualification', models.CharField(max_length=200)),
                ('stipend', models.DecimalField(decimal_places=2, max_digits=10)),
                ('year', models.IntegerField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
            ],
            options={
                'verbose_name': 'Staff Allocation',
                'verbose_name_plural': 'Staff Allocations',
                'db_table': 'staff_allocations',
            },
        ),

        # Request (db_table = 'requests')
        migrations.CreateModel(
            name='Request',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('project', models.ForeignKey(
                    db_column='project_id', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('request_type', models.CharField(
                    choices=[('funds', 'Funds Request'), ('staff', 'Staff Request')],
                    max_length=20)),
                ('description', models.TextField()),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('status', models.CharField(default='PENDING', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Request',
                'verbose_name_plural': 'Requests',
                'db_table': 'requests',
            },
        ),

        # RSPCInventory (db_table = 'rspc_inventory')
        migrations.CreateModel(
            name='RSPCInventory',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('project', models.ForeignKey(
                    db_column='project_id', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('description', models.TextField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('status', models.CharField(default='PENDING', max_length=50)),
            ],
            options={
                'verbose_name': 'RSPC Inventory',
                'verbose_name_plural': 'RSPC Inventories',
                'db_table': 'rspc_inventory',
            },
        ),

        # File (db_table = 'file')
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('uploader', models.CharField(max_length=100)),
                ('uploader_design', models.CharField(max_length=100)),
                ('receiver', models.CharField(max_length=100)),
                ('receiver_design', models.CharField(max_length=100)),
                ('src_module', models.CharField(max_length=100)),
                ('src_object_id', models.CharField(max_length=100)),
                ('subject', models.CharField(max_length=500)),
                ('attachment', models.FileField(upload_to='rspc/files/')),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'File',
                'verbose_name_plural': 'Files',
                'db_table': 'file',
            },
        ),

        # Tracking (db_table = 'tracking')
        migrations.CreateModel(
            name='Tracking',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('file', models.ForeignKey(
                    db_column='file_id', on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.file')),
                ('sender_id', models.CharField(max_length=100)),
                ('sender_design', models.CharField(max_length=100)),
                ('receiver_id', models.CharField(max_length=100)),
                ('receive_design', models.CharField(max_length=100)),
                ('receive_date', models.DateTimeField(auto_now_add=True)),
                ('remarks', models.TextField(blank=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='rspc/tracking/')),
                ('current_id', models.CharField(blank=True, max_length=100)),
                ('src_module', models.CharField(default='research_procedures', max_length=100)),
            ],
            options={
                'verbose_name': 'Tracking',
                'verbose_name_plural': 'Trackings',
                'db_table': 'tracking',
            },
        ),

        # Expenditure (db_table = 'rspc_expenditure')
        migrations.CreateModel(
            name='Expenditure',
            fields=[
                ('eid', models.AutoField(primary_key=True, serialize=False)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.project')),
                ('category', models.CharField(max_length=100)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('purpose', models.TextField()),
                ('status', models.CharField(default='PENDING', max_length=50)),
                ('requested_by', models.CharField(max_length=150)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('current_approver', models.CharField(blank=True, max_length=150, null=True)),
                ('supporting_documents', models.JSONField(default=list)),
            ],
            options={
                'verbose_name': 'Expenditure',
                'verbose_name_plural': 'Expenditures',
                'db_table': 'rspc_expenditure',
            },
        ),

        # Notification (db_table = 'rspc_notification')
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('nid', models.AutoField(primary_key=True, serialize=False)),
                ('recipient', models.CharField(max_length=150)),
                ('subject', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('entity_type', models.CharField(max_length=50)),
                ('entity_id', models.CharField(max_length=50)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
                'db_table': 'rspc_notification',
            },
        ),

        # ScheduledReport (db_table = 'rspc_scheduled_report')
        migrations.CreateModel(
            name='ScheduledReport',
            fields=[
                ('sid', models.AutoField(primary_key=True, serialize=False)),
                ('report_type', models.CharField(max_length=100)),
                ('frequency', models.CharField(max_length=50)),
                ('recipients', models.JSONField(default=list)),
                ('next_run', models.DateTimeField()),
                ('created_by', models.CharField(max_length=150)),
                ('parameters', models.JSONField(default=dict)),
            ],
            options={
                'verbose_name': 'Scheduled Report',
                'verbose_name_plural': 'Scheduled Reports',
                'db_table': 'rspc_scheduled_report',
            },
        ),
    ]

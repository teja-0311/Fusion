# Generated migration for UC-021, UC-022, UC-023, BR-020

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0009_uc017_uc018_br015'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add new fields to Project model for BR-020
        migrations.AddField(
            model_name='project',
            name='project_type',
            field=models.CharField(
                choices=[('RESEARCH', 'Research'), ('CONSULTANCY', 'Consultancy')],
                default='RESEARCH',
                help_text='BR-020: Project type',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='estimated_hours',
            field=models.IntegerField(
                blank=True,
                help_text='BR-020: Estimated consultancy hours (if consultancy project)',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='hourly_rate',
            field=models.DecimalField(
                blank=True,
                help_text='BR-020: Hourly rate for consultancy',
                max_digits=10,
                decimal_places=2,
                null=True
            ),
        ),
        
        # UC-021: SmallFundRequest model
        migrations.CreateModel(
            name='SmallFundRequest',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(help_text='Brief title of fund request', max_length=200)),
                ('description', models.TextField(help_text='Detailed description of need')),
                ('amount', models.DecimalField(
                    decimal_places=2,
                    help_text='Amount ≤ 50,000',
                    max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0.01), django.core.validators.MaxValueValidator(50000)]
                )),
                ('purpose', models.CharField(help_text='Purpose of fund', max_length=200)),
                ('justification', models.TextField(help_text='Justification for the request')),
                ('attachment_url', models.URLField(blank=True, help_text='Supporting document URL', null=True)),
                ('status', models.CharField(
                    choices=[
                        ('DRAFT', 'Draft'),
                        ('SUBMITTED', 'Submitted'),
                        ('APPROVED', 'Approved'),
                        ('REJECTED', 'Rejected'),
                        ('DISBURSED', 'Disbursed')
                    ],
                    default='DRAFT',
                    max_length=20
                )),
                ('submission_date', models.DateTimeField(blank=True, help_text='When submitted for approval', null=True)),
                ('approval_date', models.DateTimeField(blank=True, help_text='When approved', null=True)),
                ('rejection_reason', models.TextField(blank=True, help_text='Reason for rejection if rejected')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(
                    blank=True,
                    help_text='HOD who approved',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_fund_requests',
                    to=settings.AUTH_USER_MODEL
                )),
                ('project', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fund_requests',
                    to='research_procedures.project'
                )),
                ('requested_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='fund_requests',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Small Fund Request',
                'verbose_name_plural': 'Small Fund Requests',
                'db_table': 'small_fund_request',
                'ordering': ['-created_date'],
            },
        ),
        
        # UC-023: FundDisbursement model
        migrations.CreateModel(
            name='FundDisbursement',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('disbursement_date', models.DateTimeField(help_text='When funds were disbursed')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Amount disbursed', max_digits=10)),
                ('method', models.CharField(
                    choices=[
                        ('BANK', 'Bank Transfer'),
                        ('CHECK', 'Check'),
                        ('CASH', 'Cash')
                    ],
                    help_text='Method of disbursement',
                    max_length=20
                )),
                ('reference_number', models.CharField(help_text='Cheque/Bank reference number', max_length=100)),
                ('status', models.CharField(
                    choices=[
                        ('PENDING', 'Pending'),
                        ('COMPLETED', 'Completed'),
                        ('FAILED', 'Failed')
                    ],
                    default='PENDING',
                    max_length=20
                )),
                ('recipient_bank_account', models.CharField(blank=True, help_text='Recipient bank account if applicable', max_length=50)),
                ('remarks', models.TextField(blank=True, help_text='Additional remarks')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('request', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='disbursement',
                    to='research_procedures.smallfundrequest'
                )),
            ],
            options={
                'verbose_name': 'Fund Disbursement',
                'verbose_name_plural': 'Fund Disbursements',
                'db_table': 'fund_disbursement',
            },
        ),
        
        # BR-020: ConsultancyLimit model (singleton)
        migrations.CreateModel(
            name='ConsultancyLimit',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('max_consultancy_hours_per_year', models.IntegerField(
                    default=500,
                    help_text='Max consultancy hours per faculty per year'
                )),
                ('max_consultancy_percentage', models.DecimalField(
                    decimal_places=2,
                    default=20,
                    help_text='Max percentage of total workload',
                    max_digits=5
                )),
                ('max_concurrent_consultancies', models.IntegerField(
                    default=2,
                    help_text='Max simultaneous consultancy projects'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Consultancy Limit',
                'verbose_name_plural': 'Consultancy Limits',
                'db_table': 'consultancy_limit',
            },
        ),
    ]

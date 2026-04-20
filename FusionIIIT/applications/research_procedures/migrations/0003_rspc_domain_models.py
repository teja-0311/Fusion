from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0002_rspc_new_models'),
        ('globals', '0001_initial'),
        ('programme_curriculum', '0001_initial'),
        ('academic_information', '0001_initial'),
    ]

    operations = [

        # ── ResearchGroup (rspc_research_group) ──────────────────────────────
        migrations.CreateModel(
            name='ResearchGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('acronym', models.CharField(blank=True, max_length=20)),
                ('description', models.TextField()),
                ('established_date', models.DateField(null=True)),
                ('website', models.URLField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('discipline', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='programme_curriculum.discipline')),
                ('head', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='led_groups',
                    to='globals.faculty')),
                ('members', models.ManyToManyField(
                    related_name='research_groups',
                    to='globals.Faculty')),
            ],
            options={
                'verbose_name': 'Research Group',
                'verbose_name_plural': 'Research Groups',
                'db_table': 'rspc_research_group',
            },
        ),

        # ── ResearchArea (rspc_research_area) ────────────────────────────────
        migrations.CreateModel(
            name='ResearchArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('discipline', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='programme_curriculum.discipline')),
                ('faculty_experts', models.ManyToManyField(
                    related_name='expertise_areas',
                    to='globals.Faculty')),
                ('parent_area', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='research_procedures.researcharea')),
            ],
            options={
                'verbose_name': 'Research Area',
                'verbose_name_plural': 'Research Areas',
                'db_table': 'rspc_research_area',
            },
        ),

        # ── FundingAgency (rspc_funding_agency) ──────────────────────────────
        migrations.CreateModel(
            name='FundingAgency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('acronym', models.CharField(blank=True, max_length=20)),
                ('agency_type', models.CharField(
                    choices=[
                        ('GOVERNMENT', 'Government'), ('PRIVATE', 'Private'),
                        ('INTERNATIONAL', 'International'), ('INDUSTRY', 'Industry'),
                        ('OTHER', 'Other'),
                    ],
                    max_length=20)),
                ('country', models.CharField(default='India', max_length=50)),
                ('website', models.URLField(blank=True)),
                ('contact_info', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Funding Agency',
                'verbose_name_plural': 'Funding Agencies',
                'db_table': 'rspc_funding_agency',
            },
        ),

        # ── SponsoredProject (rspc_sponsored_project) ─────────────────────────
        migrations.CreateModel(
            name='SponsoredProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=500)),
                ('project_number', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField()),
                ('sanctioned_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('utilized_amount', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('submission_date', models.DateField(blank=True, null=True)),
                ('sanction_date', models.DateField(blank=True, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('original_end_date', models.DateField(blank=True, null=True)),
                ('extended_end_date', models.DateField(blank=True, null=True)),
                ('actual_end_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('PROPOSED', 'Proposed'), ('SUBMITTED', 'Submitted'),
                        ('UNDER_REVIEW', 'Under Review'), ('SANCTIONED', 'Sanctioned'),
                        ('ONGOING', 'Ongoing'), ('EXTENDED', 'Extended'),
                        ('COMPLETED', 'Completed'), ('TERMINATED', 'Terminated'),
                        ('REJECTED', 'Rejected'),
                    ],
                    default='PROPOSED', max_length=20)),
                ('proposal_document', models.FileField(
                    blank=True, null=True, upload_to='rspc/projects/proposals/')),
                ('sanction_letter', models.FileField(
                    blank=True, null=True, upload_to='rspc/projects/sanctions/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('funding_agency', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='research_procedures.fundingagency')),
                ('principal_investigator', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='pi_projects',
                    to='globals.faculty')),
                ('co_principal_investigators', models.ManyToManyField(
                    blank=True, related_name='copi_projects', to='globals.Faculty')),
                ('research_area', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to='research_procedures.researcharea')),
                ('research_scholars', models.ManyToManyField(
                    blank=True, related_name='sponsored_projects',
                    to='academic_information.student')),
            ],
            options={
                'verbose_name': 'Sponsored Project',
                'verbose_name_plural': 'Sponsored Projects',
                'db_table': 'rspc_sponsored_project',
            },
        ),

        # ── ProjectExpenditure (rspc_project_expenditure) ─────────────────────
        migrations.CreateModel(
            name='ProjectExpenditure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('expenditure_head', models.CharField(
                    choices=[
                        ('MANPOWER', 'Manpower'), ('EQUIPMENT', 'Equipment'),
                        ('CONSUMABLES', 'Consumables'), ('TRAVEL', 'Travel'),
                        ('CONTINGENCY', 'Contingency'), ('OVERHEAD', 'Overhead'),
                        ('OTHER', 'Other'),
                    ],
                    max_length=20)),
                ('description', models.TextField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('date', models.DateField()),
                ('voucher_number', models.CharField(blank=True, max_length=50)),
                ('bill_document', models.FileField(
                    blank=True, null=True, upload_to='rspc/projects/bills/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approved_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to='globals.extrainfo')),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='expenditures',
                    to='research_procedures.sponsoredproject')),
            ],
            options={
                'verbose_name': 'Project Expenditure',
                'verbose_name_plural': 'Project Expenditures',
                'db_table': 'rspc_project_expenditure',
            },
        ),

        # ── ProjectMilestone (rspc_project_milestone) ─────────────────────────
        migrations.CreateModel(
            name='ProjectMilestone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('due_date', models.DateField()),
                ('completed_date', models.DateField(blank=True, null=True)),
                ('is_completed', models.BooleanField(default=False)),
                ('deliverables', models.TextField(blank=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='milestones',
                    to='research_procedures.sponsoredproject')),
            ],
            options={
                'verbose_name': 'Project Milestone',
                'verbose_name_plural': 'Project Milestones',
                'db_table': 'rspc_project_milestone',
            },
        ),

        # ── ProjectReport (rspc_project_report) ───────────────────────────────
        migrations.CreateModel(
            name='ProjectReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('report_type', models.CharField(
                    choices=[
                        ('QUARTERLY', 'Quarterly'), ('HALF_YEARLY', 'Half Yearly'),
                        ('ANNUAL', 'Annual'), ('FINAL', 'Final'),
                        ('UTILIZATION', 'Utilization Certificate'),
                    ],
                    max_length=20)),
                ('period_from', models.DateField()),
                ('period_to', models.DateField()),
                ('summary', models.TextField()),
                ('report_file', models.FileField(upload_to='rspc/projects/reports/')),
                ('submitted_date', models.DateField()),
                ('approved', models.BooleanField(default=False)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reports',
                    to='research_procedures.sponsoredproject')),
            ],
            options={
                'verbose_name': 'Project Report',
                'verbose_name_plural': 'Project Reports',
                'db_table': 'rspc_project_report',
            },
        ),

        # ── ConsultancyProject (rspc_consultancy_project) ─────────────────────
        migrations.CreateModel(
            name='ConsultancyProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=500)),
                ('project_number', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField()),
                ('client_name', models.CharField(max_length=200)),
                ('client_type', models.CharField(max_length=50)),
                ('client_contact', models.TextField(blank=True, null=True)),
                ('contract_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('faculty_share', models.DecimalField(decimal_places=2, max_digits=15)),
                ('institute_share', models.DecimalField(decimal_places=2, max_digits=15)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(
                    choices=[
                        ('PROPOSED', 'Proposed'), ('NEGOTIATION', 'Under Negotiation'),
                        ('APPROVED', 'Approved'), ('ONGOING', 'Ongoing'),
                        ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'),
                    ],
                    default='PROPOSED', max_length=20)),
                ('agreement_document', models.FileField(
                    blank=True, null=True, upload_to='rspc/consultancy/agreements/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('consultant', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='consultancies',
                    to='globals.faculty')),
                ('co_consultants', models.ManyToManyField(
                    blank=True, related_name='co_consultancies', to='globals.Faculty')),
            ],
            options={
                'verbose_name': 'Consultancy Project',
                'verbose_name_plural': 'Consultancy Projects',
                'db_table': 'rspc_consultancy_project',
            },
        ),

        # ── Publication (rspc_publication) ────────────────────────────────────
        migrations.CreateModel(
            name='Publication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=500)),
                ('publication_type', models.CharField(
                    choices=[
                        ('JOURNAL', 'Journal Article'), ('CONFERENCE', 'Conference Paper'),
                        ('BOOK', 'Book'), ('BOOK_CHAPTER', 'Book Chapter'),
                        ('PATENT', 'Patent'), ('THESIS', 'Thesis'),
                        ('TECHNICAL_REPORT', 'Technical Report'), ('OTHER', 'Other'),
                    ],
                    max_length=20)),
                ('external_authors', models.TextField(blank=True)),
                ('journal_conference_name', models.CharField(max_length=300)),
                ('publisher', models.CharField(blank=True, max_length=200)),
                ('volume', models.CharField(blank=True, max_length=20)),
                ('issue', models.CharField(blank=True, max_length=20)),
                ('pages', models.CharField(blank=True, max_length=20)),
                ('year', models.IntegerField()),
                ('month', models.IntegerField(blank=True, null=True)),
                ('index_type', models.CharField(
                    choices=[
                        ('SCI', 'SCI'), ('SCIE', 'SCIE'), ('SCOPUS', 'Scopus'),
                        ('WOS', 'Web of Science'), ('UGCCL', 'UGC Care List'),
                        ('OTHER', 'Other'), ('NONE', 'Non-indexed'),
                    ],
                    default='NONE', max_length=20)),
                ('impact_factor', models.DecimalField(
                    blank=True, decimal_places=3, max_digits=6, null=True)),
                ('doi', models.CharField(blank=True, max_length=100)),
                ('issn', models.CharField(blank=True, max_length=20)),
                ('isbn', models.CharField(blank=True, max_length=20)),
                ('url', models.URLField(blank=True)),
                ('pdf_file', models.FileField(
                    blank=True, null=True, upload_to='rspc/publications/')),
                ('is_verified', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('faculty_authors', models.ManyToManyField(
                    related_name='publications', to='globals.Faculty')),
                ('student_authors', models.ManyToManyField(
                    blank=True, related_name='publications',
                    to='academic_information.student')),
                ('verified_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='globals.extrainfo')),
            ],
            options={
                'verbose_name': 'Publication',
                'verbose_name_plural': 'Publications',
                'db_table': 'rspc_publication',
            },
        ),

        # ── Patent (rspc_patent) ──────────────────────────────────────────────
        migrations.CreateModel(
            name='Patent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=500)),
                ('abstract', models.TextField()),
                ('patent_type', models.CharField(
                    choices=[
                        ('NATIONAL', 'National'), ('INTERNATIONAL', 'International'),
                        ('PCT', 'PCT'),
                    ],
                    max_length=20)),
                ('external_inventors', models.TextField(blank=True)),
                ('application_number', models.CharField(blank=True, max_length=50)),
                ('filing_date', models.DateField(blank=True, null=True)),
                ('publication_number', models.CharField(blank=True, max_length=50)),
                ('publication_date', models.DateField(blank=True, null=True)),
                ('grant_number', models.CharField(blank=True, max_length=50)),
                ('grant_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('DRAFT', 'Draft'), ('FILED', 'Filed'), ('PUBLISHED', 'Published'),
                        ('UNDER_EXAMINATION', 'Under Examination'), ('GRANTED', 'Granted'),
                        ('REJECTED', 'Rejected'), ('LAPSED', 'Lapsed'),
                    ],
                    default='DRAFT', max_length=20)),
                ('specification_document', models.FileField(
                    blank=True, null=True, upload_to='rspc/patents/specs/')),
                ('grant_certificate', models.FileField(
                    blank=True, null=True, upload_to='rspc/patents/certificates/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('faculty_inventors', models.ManyToManyField(
                    related_name='patents', to='globals.Faculty')),
                ('student_inventors', models.ManyToManyField(
                    blank=True, related_name='patents',
                    to='academic_information.student')),
                ('related_project', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='research_procedures.sponsoredproject')),
            ],
            options={
                'verbose_name': 'Patent',
                'verbose_name_plural': 'Patents',
                'db_table': 'rspc_patent',
            },
        ),

        # ── ResearchScholar (rspc_research_scholar) ───────────────────────────
        migrations.CreateModel(
            name='ResearchScholar',
            fields=[
                ('student', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True, serialize=False,
                    to='academic_information.student')),
                ('enrollment_date', models.DateField()),
                ('expected_completion', models.DateField(blank=True, null=True)),
                ('fellowship_type', models.CharField(blank=True, max_length=50)),
                ('fellowship_amount', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=10, null=True)),
                ('coursework_completed', models.BooleanField(default=False)),
                ('comprehensive_exam_passed', models.BooleanField(default=False)),
                ('comprehensive_exam_date', models.DateField(blank=True, null=True)),
                ('synopsis_submitted', models.BooleanField(default=False)),
                ('synopsis_date', models.DateField(blank=True, null=True)),
                ('thesis_submitted', models.BooleanField(default=False)),
                ('thesis_submission_date', models.DateField(blank=True, null=True)),
                ('defense_date', models.DateField(blank=True, null=True)),
                ('degree_awarded_date', models.DateField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Research Scholar',
                'verbose_name_plural': 'Research Scholars',
                'db_table': 'rspc_research_scholar',
            },
        ),

        # ── Committee (rspc_committee) ────────────────────────────────────────
        migrations.CreateModel(
            name='Committee',
            fields=[
                ('committee_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('deadline', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('members', models.ManyToManyField(
                    related_name='committees', to='globals.ExtraInfo')),
                ('staff', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.staff')),
            ],
            options={
                'verbose_name': 'Committee',
                'verbose_name_plural': 'Committees',
                'db_table': 'rspc_committee',
            },
        ),

        # ── CommitteeVerdict (rspc_committee_verdict) ─────────────────────────
        migrations.CreateModel(
            name='CommitteeVerdict',
            fields=[
                ('verdict_id', models.AutoField(primary_key=True, serialize=False)),
                ('decision', models.CharField(
                    choices=[
                        ('APPROVE', 'Approve'), ('REJECT', 'Reject'), ('ABSTAIN', 'Abstain'),
                    ],
                    max_length=20)),
                ('comments', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('committee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='research_procedures.committee')),
                ('member', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='globals.extrainfo')),
            ],
            options={
                'verbose_name': 'Committee Verdict',
                'verbose_name_plural': 'Committee Verdicts',
                'db_table': 'rspc_committee_verdict',
            },
        ),
        migrations.AlterUniqueTogether(
            name='committeeverdict',
            unique_together={('committee', 'member')},
        ),
    ]

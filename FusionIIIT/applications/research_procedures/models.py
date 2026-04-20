"""
RSPC Module - Database Models and Constants
All TextChoices/IntegerChoices defined here for centralized data definitions
Based on Integration Guide and views.py analysis
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from typing import Tuple
from applications.globals.models import ExtraInfo, Faculty, DepartmentInfo, Designation, HoldsDesignation
from applications.academic_information.models import Student
from applications.programme_curriculum.models import Discipline, Programme



# ============================================================================
# CONSTANTS - TextChoices
# ============================================================================

class AgencyType(models.TextChoices):
    """Funding agency types"""
    GOVERNMENT = 'GOVERNMENT', 'Government'
    PRIVATE = 'PRIVATE', 'Private'
    INTERNATIONAL = 'INTERNATIONAL', 'International'
    INDUSTRY = 'INDUSTRY', 'Industry'
    OTHER = 'OTHER', 'Other'


class ProjectStatus(models.TextChoices):
    """Project status choices"""
    PROPOSED = 'PROPOSED', 'Proposed'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    SANCTIONED = 'SANCTIONED', 'Sanctioned'
    ONGOING = 'ONGOING', 'Ongoing'
    EXTENDED = 'EXTENDED', 'Extended'
    COMPLETED = 'COMPLETED', 'Completed'
    TERMINATED = 'TERMINATED', 'Terminated'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ProjectAccessMode(models.TextChoices):
    """Project access modes for Co-PIs"""
    CO = 'Co', 'Co-PI can modify'
    NOCO = 'noCo', 'Only PI can modify'


class ExpenditureHead(models.TextChoices):
    """Expenditure categories"""
    MANPOWER = 'MANPOWER', 'Manpower'
    EQUIPMENT = 'EQUIPMENT', 'Equipment'
    CONSUMABLES = 'CONSUMABLES', 'Consumables'
    TRAVEL = 'TRAVEL', 'Travel'
    CONTINGENCY = 'CONTINGENCY', 'Contingency'
    OVERHEAD = 'OVERHEAD', 'Overhead'
    OTHER = 'OTHER', 'Other'


class ReportType(models.TextChoices):
    """Project report types"""
    QUARTERLY = 'QUARTERLY', 'Quarterly'
    HALF_YEARLY = 'HALF_YEARLY', 'Half Yearly'
    ANNUAL = 'ANNUAL', 'Annual'
    FINAL = 'FINAL', 'Final'
    UTILIZATION = 'UTILIZATION', 'Utilization Certificate'


class ConsultancyStatus(models.TextChoices):
    """Consultancy project status"""
    PROPOSED = 'PROPOSED', 'Proposed'
    NEGOTIATION = 'NEGOTIATION', 'Under Negotiation'
    APPROVED = 'APPROVED', 'Approved'
    ONGOING = 'ONGOING', 'Ongoing'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PublicationType(models.TextChoices):
    """Publication types"""
    JOURNAL = 'JOURNAL', 'Journal Article'
    CONFERENCE = 'CONFERENCE', 'Conference Paper'
    BOOK = 'BOOK', 'Book'
    BOOK_CHAPTER = 'BOOK_CHAPTER', 'Book Chapter'
    PATENT = 'PATENT', 'Patent'
    THESIS = 'THESIS', 'Thesis'
    TECHNICAL_REPORT = 'TECHNICAL_REPORT', 'Technical Report'
    OTHER = 'OTHER', 'Other'


class IndexType(models.TextChoices):
    """Journal indexing types"""
    SCI = 'SCI', 'SCI'
    SCIE = 'SCIE', 'SCIE'
    SCOPUS = 'SCOPUS', 'Scopus'
    WOS = 'WOS', 'Web of Science'
    UGCCL = 'UGCCL', 'UGC Care List'
    OTHER = 'OTHER', 'Other'
    NONE = 'NONE', 'Non-indexed'


class PatentStatus(models.TextChoices):
    """Patent status choices"""
    DRAFT = 'DRAFT', 'Draft'
    FILED = 'FILED', 'Filed'
    PUBLISHED = 'PUBLISHED', 'Published'
    UNDER_EXAMINATION = 'UNDER_EXAMINATION', 'Under Examination'
    GRANTED = 'GRANTED', 'Granted'
    REJECTED = 'REJECTED', 'Rejected'
    LAPSED = 'LAPSED', 'Lapsed'


class PatentType(models.TextChoices):
    """Patent type choices"""
    NATIONAL = 'NATIONAL', 'National'
    INTERNATIONAL = 'INTERNATIONAL', 'International'
    PCT = 'PCT', 'PCT'


class RequestType(models.TextChoices):
    """Request types for project requests"""
    FUNDS = 'funds', 'Funds Request'
    STAFF = 'staff', 'Staff Request'


class RequestStatus(models.TextChoices):
    """Request status choices"""
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    PROCESSING = 'PROCESSING', 'Processing'


class StaffType(models.TextChoices):
    """Staff position types"""
    RA = 'RA', 'Research Associate'
    SRF = 'SRF', 'Senior Research Fellow'
    JRF = 'JRF', 'Junior Research Fellow'
    PROJECT_ASSISTANT = 'PROJECT_ASSISTANT', 'Project Assistant'
    PROJECT_SCIENTIST = 'PROJECT_SCIENTIST', 'Project Scientist'
    OTHER = 'OTHER', 'Other'


class StaffApprovalStatus(models.TextChoices):
    """Staff approval status"""
    DRAFT = 'DRAFT', 'Draft'
    COMMITTEE_PENDING = 'COMMITTEE_PENDING', 'Committee Pending'
    COMMITTEE_APPROVED = 'COMMITTEE_APPROVED', 'Committee Approved'
    COMMITTEE_REJECTED = 'COMMITTEE_REJECTED', 'Committee Rejected'
    HOD_PENDING = 'HOD_PENDING', 'HOD Pending'
    HOD_APPROVED = 'HOD_APPROVED', 'HOD Approved'
    HOD_REJECTED = 'HOD_REJECTED', 'HOD Rejected'
    RSPC_PENDING = 'RSPC_PENDING', 'RSPC Pending'
    RSPC_APPROVED = 'RSPC_APPROVED', 'RSPC Approved'
    RSPC_REJECTED = 'RSPC_REJECTED', 'RSPC Rejected'
    APPOINTED = 'APPOINTED', 'Appointed'
    REJECTED = 'REJECTED', 'Rejected'


class CommitteeDecision(models.TextChoices):
    """Committee member decision"""
    APPROVE = 'APPROVE', 'Approve'
    REJECT = 'REJECT', 'Reject'
    ABSTAIN = 'ABSTAIN', 'Abstain'


class ChangeType(models.TextChoices):
    """Types of changes to project (UC-004)"""
    TITLE = 'TITLE', 'Title'
    BUDGET = 'BUDGET', 'Budget'
    DESCRIPTION = 'DESCRIPTION', 'Description'
    MEMBERS = 'MEMBERS', 'Members'
    OTHER = 'OTHER', 'Other'


class CancellationRequestStatus(models.TextChoices):
    """Cancellation request approval status (UC-005)"""
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class VettingStatus(models.TextChoices):
    """Vetting outcome status (UC-012)"""
    PASS = 'PASS', 'Pass'
    FAIL = 'FAIL', 'Fail'
    FLAG = 'FLAG', 'Flag'


class ProposalVettingStatus(models.TextChoices):
    """Proposal vetting workflow status (UC-012)"""
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class SmallFundRequestStatus(models.TextChoices):
    """Small fund request status (UC-021, UC-022, UC-023)"""
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    DISBURSED = 'DISBURSED', 'Disbursed'


class DisbursementMethod(models.TextChoices):
    """Fund disbursement method (UC-023)"""
    BANK = 'BANK', 'Bank Transfer'
    CHECK = 'CHECK', 'Check'
    CASH = 'CASH', 'Cash'


class DisbursementStatus(models.TextChoices):
    """Disbursement status (UC-023)"""
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class ProjectTypeChoice(models.TextChoices):
    """Project type choices (BR-020: Support CONSULTANCY type)"""
    RESEARCH = 'RESEARCH', 'Research'
    CONSULTANCY = 'CONSULTANCY', 'Consultancy'


# ============================================================================
# RESEARCH AREAS MODELS
# ============================================================================

class ResearchGroup(models.Model):
    """
    Research groups/labs in the institute
    """
    name = models.CharField(max_length=200, unique=True)
    acronym = models.CharField(max_length=20, blank=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    description = models.TextField()
    head = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, related_name='led_groups')
    members = models.ManyToManyField(Faculty, related_name='research_groups')
    established_date = models.DateField(null=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rspc_research_group'
        verbose_name = 'Research Group'
        verbose_name_plural = 'Research Groups'
        ordering = ['-created_date']

    def __str__(self):
        return f"{self.name} ({self.acronym})"


class ResearchArea(models.Model):
    """
    Research areas and specializations
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parent_area = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_areas')
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    faculty_experts = models.ManyToManyField(Faculty, related_name='expertise_areas')
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rspc_research_area'
        verbose_name = 'Research Area'
        verbose_name_plural = 'Research Areas'
        ordering = ['-created_date']

    def __str__(self):
        return self.name


# ============================================================================
# SPONSORED PROJECTS MODELS
# ============================================================================

class FundingAgency(models.Model):
    """
    Funding agencies (SERB, DST, DRDO, etc.)
    """
    name = models.CharField(max_length=200)
    acronym = models.CharField(max_length=20, blank=True)
    agency_type = models.CharField(max_length=20, choices=AgencyType.choices)
    country = models.CharField(max_length=50, default='India')
    website = models.URLField(blank=True)
    contact_info = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'rspc_funding_agency'
        verbose_name = 'Funding Agency'
        verbose_name_plural = 'Funding Agencies'

    def __str__(self):
        return f"{self.name} ({self.acronym})" if self.acronym else self.name


class SponsoredProject(models.Model):
    """
    Sponsored research projects
    """
    # Basic info
    title = models.CharField(max_length=500)
    project_number = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    research_area = models.ForeignKey(ResearchArea, on_delete=models.SET_NULL, null=True)
    
    # Team
    principal_investigator = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name='pi_projects')
    co_principal_investigators = models.ManyToManyField(Faculty, related_name='copi_projects', blank=True)
    research_scholars = models.ManyToManyField(Student, related_name='sponsored_projects', blank=True)
    
    # Funding
    funding_agency = models.ForeignKey(FundingAgency, on_delete=models.PROTECT)
    sanctioned_amount = models.DecimalField(max_digits=15, decimal_places=2)
    utilized_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Timeline
    submission_date = models.DateField(null=True, blank=True)
    sanction_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    original_end_date = models.DateField(null=True, blank=True)
    extended_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PROPOSED)
    
    # Files
    proposal_document = models.FileField(upload_to='rspc/projects/proposals/', null=True, blank=True)
    sanction_letter = models.FileField(upload_to='rspc/projects/sanctions/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rspc_sponsored_project'
        verbose_name = 'Sponsored Project'
        verbose_name_plural = 'Sponsored Projects'

    def __str__(self):
        return f"{self.project_number} - {self.title}"


class ProjectExpenditure(models.Model):
    """
    Project expenditure tracking
    """
    project = models.ForeignKey(SponsoredProject, on_delete=models.CASCADE, related_name='expenditures')
    expenditure_head = models.CharField(max_length=20, choices=ExpenditureHead.choices)
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    voucher_number = models.CharField(max_length=50, blank=True)
    bill_document = models.FileField(upload_to='rspc/projects/bills/', null=True, blank=True)
    approved_by = models.ForeignKey(ExtraInfo, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rspc_project_expenditure'
        verbose_name = 'Project Expenditure'
        verbose_name_plural = 'Project Expenditures'

    def __str__(self):
        return f"{self.project.project_number} - {self.expenditure_head} - {self.amount}"


class ProjectMilestone(models.Model):
    """
    Project milestones and deliverables
    """
    project = models.ForeignKey(SponsoredProject, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    deliverables = models.TextField(blank=True)

    class Meta:
        db_table = 'rspc_project_milestone'
        verbose_name = 'Project Milestone'
        verbose_name_plural = 'Project Milestones'

    def __str__(self):
        return f"{self.project.project_number} - {self.title}"


class ProjectReport(models.Model):
    """
    Project progress reports
    """
    project = models.ForeignKey(SponsoredProject, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    period_from = models.DateField()
    period_to = models.DateField()
    summary = models.TextField()
    report_file = models.FileField(upload_to='rspc/projects/reports/')
    submitted_date = models.DateField()
    approved = models.BooleanField(default=False)

    class Meta:
        db_table = 'rspc_project_report'
        verbose_name = 'Project Report'
        verbose_name_plural = 'Project Reports'

    def __str__(self):
        return f"{self.project.project_number} - {self.report_type} ({self.period_from} to {self.period_to})"


# ============================================================================
# CONSULTANCY MODELS
# ============================================================================

class ConsultancyProject(models.Model):
    """
    Consultancy projects
    """
    # Basic info
    title = models.CharField(max_length=500)
    project_number = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    
    # Client
    client_name = models.CharField(max_length=200)
    client_type = models.CharField(max_length=50)  # Industry, Government, etc.
    client_contact = models.TextField(blank=True, null=True)
    
    # Team
    consultant = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name='consultancies')
    co_consultants = models.ManyToManyField(Faculty, related_name='co_consultancies', blank=True)
    
    # Financial
    contract_amount = models.DecimalField(max_digits=15, decimal_places=2)
    faculty_share = models.DecimalField(max_digits=15, decimal_places=2)
    institute_share = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Timeline
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Status
    status = models.CharField(max_length=20, choices=ConsultancyStatus.choices, default=ConsultancyStatus.PROPOSED)
    
    # Documents
    agreement_document = models.FileField(upload_to='rspc/consultancy/agreements/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rspc_consultancy_project'
        verbose_name = 'Consultancy Project'
        verbose_name_plural = 'Consultancy Projects'

    def __str__(self):
        return f"{self.project_number} - {self.title}"


# ============================================================================
# PUBLICATIONS MODELS
# ============================================================================

class Publication(models.Model):
    """
    Research publications
    """
    # Basic info
    title = models.CharField(max_length=500)
    publication_type = models.CharField(max_length=20, choices=PublicationType.choices)
    
    # Authors (from institute)
    faculty_authors = models.ManyToManyField(Faculty, related_name='publications')
    student_authors = models.ManyToManyField(Student, related_name='publications', blank=True)
    external_authors = models.TextField(blank=True)  # Names of external authors
    
    # Publication details
    journal_conference_name = models.CharField(max_length=300)
    publisher = models.CharField(max_length=200, blank=True)
    volume = models.CharField(max_length=20, blank=True)
    issue = models.CharField(max_length=20, blank=True)
    pages = models.CharField(max_length=20, blank=True)
    year = models.IntegerField()
    month = models.IntegerField(null=True, blank=True)
    
    # Indexing
    index_type = models.CharField(max_length=20, choices=IndexType.choices, default=IndexType.NONE)
    impact_factor = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    
    # Identifiers
    doi = models.CharField(max_length=100, blank=True)
    issn = models.CharField(max_length=20, blank=True)
    isbn = models.CharField(max_length=20, blank=True)
    url = models.URLField(blank=True)
    
    # File
    pdf_file = models.FileField(upload_to='rspc/publications/', null=True, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(ExtraInfo, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rspc_publication'
        verbose_name = 'Publication'
        verbose_name_plural = 'Publications'

    def __str__(self):
        return f"{self.title} ({self.year})"


# ============================================================================
# PATENTS MODELS
# ============================================================================

class Patent(models.Model):
    """
    Patent applications and grants
    """
    # Basic info
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    patent_type = models.CharField(max_length=20, choices=PatentType.choices)
    
    # Inventors
    faculty_inventors = models.ManyToManyField(Faculty, related_name='patents')
    student_inventors = models.ManyToManyField(Student, related_name='patents', blank=True)
    external_inventors = models.TextField(blank=True)
    
    # Filing details
    application_number = models.CharField(max_length=50, blank=True)
    filing_date = models.DateField(null=True, blank=True)
    publication_number = models.CharField(max_length=50, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    grant_number = models.CharField(max_length=50, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PatentStatus.choices, default=PatentStatus.DRAFT)
    
    # Documents
    specification_document = models.FileField(upload_to='rspc/patents/specs/', null=True, blank=True)
    grant_certificate = models.FileField(upload_to='rspc/patents/certificates/', null=True, blank=True)
    
    # Related project (if any)
    related_project = models.ForeignKey(SponsoredProject, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rspc_patent'
        verbose_name = 'Patent'
        verbose_name_plural = 'Patents'

    def __str__(self):
        return f"{self.title} - {self.status}"


# ============================================================================
# RESEARCH SCHOLARS MODELS
# ============================================================================

class ResearchScholar(models.Model):
    """
    Extended information for research scholars
    """
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    
    # Supervisor info (linked from ThesisTopicProcess)
    enrollment_date = models.DateField()
    expected_completion = models.DateField(null=True, blank=True)
    
    # Fellowship
    fellowship_type = models.CharField(max_length=50, blank=True)  # GATE, NET, Institute, etc.
    fellowship_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Progress
    coursework_completed = models.BooleanField(default=False)
    comprehensive_exam_passed = models.BooleanField(default=False)
    comprehensive_exam_date = models.DateField(null=True, blank=True)
    
    # Synopsis
    synopsis_submitted = models.BooleanField(default=False)
    synopsis_date = models.DateField(null=True, blank=True)
    
    # Thesis
    thesis_submitted = models.BooleanField(default=False)
    thesis_submission_date = models.DateField(null=True, blank=True)
    defense_date = models.DateField(null=True, blank=True)
    degree_awarded_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'rspc_research_scholar'
        verbose_name = 'Research Scholar'
        verbose_name_plural = 'Research Scholars'

    def __str__(self):
        return f"Scholar: {self.student.id}"


# ============================================================================
# CORE PROJECT MANAGEMENT MODELS (from views.py analysis)
# ============================================================================

class Project(models.Model):
    """
    Core Project entity (from views.py analysis)
    Maps to 'projects' table in database
    """
    pid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)  # BR-RSPC-05: Unique project name
    pi_id = models.CharField(max_length=100)  # Principal Investigator ID
    pi_name = models.CharField(max_length=200)
    access = models.CharField(max_length=10, choices=ProjectAccessMode.choices, default=ProjectAccessMode.NOCO)
    type = models.CharField(max_length=50)  # Research, Consultancy, etc.
    dept = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    sponsored_agency = models.CharField(max_length=200)
    scheme = models.CharField(max_length=100)
    description = models.TextField()
    duration = models.IntegerField(validators=[MinValueValidator(6), MaxValueValidator(60)])  # BR-RSPC-011: 6 months to 5 years
    submission_date = models.DateTimeField()
    total_budget = models.DecimalField(max_digits=15, decimal_places=2)
    sanction_date = models.DateTimeField(null=True, blank=True)
    sanctioned_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    initial_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    file = models.FileField(upload_to='rspc/projects/', null=True, blank=True)
    registration_form = models.FileField(upload_to='rspc/registrations/', null=True, blank=True)
    status = models.CharField(max_length=50, default='PROPOSED')
    financial_outlay_status = models.IntegerField(default=0)  # 0: Not added, 1: Added
    end_report = models.FileField(upload_to='rspc/closure/', null=True, blank=True)
    end_approval = models.BooleanField(default=False)
    years = models.IntegerField(default=1)  # Project duration in years
    end_date = models.DateField(null=True, blank=True)
    
    # For file tracking
    file_id = models.CharField(max_length=100, null=True, blank=True)
    
    # BR-018: Approval SLA fields
    approval_deadline = models.DateTimeField(null=True, blank=True, help_text="Approval deadline (10 days from submission)")
    approval_status_escalated = models.BooleanField(default=False, help_text="BR-018: Has approval been escalated?")
    escalation_date = models.DateTimeField(null=True, blank=True, help_text="When approval was escalated")
    
    # UC-004: Update tracking fields
    allow_updates_after_approval = models.BooleanField(default=False, help_text="BR-011: Allow updates post-approval")
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects_updated')
    last_updated_date = models.DateTimeField(null=True, blank=True)
    
    # UC-005: Cancellation fields
    cancellation_reason = models.TextField(blank=True, help_text="Reason for project cancellation")
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects_cancelled')
    cancelled_date = models.DateTimeField(null=True, blank=True)
    
    # UC-012: HOD vetting fields
    hod_vetting_status = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')],
        default='PENDING',
        help_text="BR-RSPC-10: HOD vetting status"
    )
    hod_vetting_date = models.DateTimeField(null=True, blank=True)
    
    # BR-020: Consultancy project type and workload fields
    project_type = models.CharField(max_length=20, choices=ProjectTypeChoice.choices, default=ProjectTypeChoice.RESEARCH, help_text="BR-020: Project type")
    estimated_hours = models.IntegerField(null=True, blank=True, help_text="BR-020: Estimated consultancy hours (if consultancy project)")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="BR-020: Hourly rate for consultancy")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f"{self.pid} - {self.name}"


# ============================================================================
# UC-021/022/023: SMALL FUND REQUEST MANAGEMENT MODELS
# ============================================================================

class SmallFundRequest(models.Model):
    """
    UC-021: Submit Small Fund Request
    Small grant requests up to 50K for research/development needs
    Status workflow: DRAFT → SUBMITTED → APPROVED/REJECTED → DISBURSED
    """
    request_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='fund_requests')
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='fund_requests')
    
    # Request details
    title = models.CharField(max_length=200, help_text="Brief title of fund request")
    description = models.TextField(help_text="Detailed description of need")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01), MaxValueValidator(50000)], help_text="Amount ≤ 50,000")
    purpose = models.CharField(max_length=200, help_text="Purpose of fund")
    justification = models.TextField(help_text="Justification for the request")
    attachment_url = models.URLField(null=True, blank=True, help_text="Supporting document URL")
    
    # Status workflow
    status = models.CharField(max_length=20, choices=SmallFundRequestStatus.choices, default=SmallFundRequestStatus.DRAFT)
    submission_date = models.DateTimeField(null=True, blank=True, help_text="When submitted for approval")
    approval_date = models.DateTimeField(null=True, blank=True, help_text="When approved")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_fund_requests', help_text="HOD who approved")
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection if rejected")
    
    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'small_fund_request'
        verbose_name = 'Small Fund Request'
        verbose_name_plural = 'Small Fund Requests'
        ordering = ['-created_date']
    
    def __str__(self):
        return f"Fund Request: {self.title} (₹{self.amount})"


class FundDisbursement(models.Model):
    """
    UC-023: Track Fund Disbursement
    Tracks disbursement of approved small fund requests
    """
    id = models.AutoField(primary_key=True)
    request = models.OneToOneField(SmallFundRequest, on_delete=models.CASCADE, related_name='disbursement')
    disbursement_date = models.DateTimeField(help_text="When funds were disbursed")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount disbursed")
    method = models.CharField(max_length=20, choices=DisbursementMethod.choices, help_text="Method of disbursement")
    reference_number = models.CharField(max_length=100, help_text="Cheque/Bank reference number")
    status = models.CharField(max_length=20, choices=DisbursementStatus.choices, default=DisbursementStatus.PENDING)
    recipient_bank_account = models.CharField(max_length=50, blank=True, help_text="Recipient bank account if applicable")
    remarks = models.TextField(blank=True, help_text="Additional remarks")
    
    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fund_disbursement'
        verbose_name = 'Fund Disbursement'
        verbose_name_plural = 'Fund Disbursements'
    
    def __str__(self):
        return f"Disbursement for Request {self.request.request_id} (₹{self.amount})"


# ============================================================================
# BR-020: CONSULTANCY WORKLOAD MANAGEMENT MODELS
# ============================================================================

class ConsultancyLimit(models.Model):
    """
    BR-020: Consultancy Workload Limits (Singleton)
    Global limits for faculty consultancy work
    """
    id = models.AutoField(primary_key=True)
    max_consultancy_hours_per_year = models.IntegerField(default=500, help_text="Max consultancy hours per faculty per year")
    max_consultancy_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20, help_text="Max percentage of total workload")
    max_concurrent_consultancies = models.IntegerField(default=2, help_text="Max simultaneous consultancy projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'consultancy_limit'
        verbose_name = 'Consultancy Limit'
        verbose_name_plural = 'Consultancy Limits'
    
    def __str__(self):
        return f"Consultancy Limits (Max: {self.max_consultancy_hours_per_year} hrs/year)"
    
    @classmethod
    def get_limits(cls):
        """Get or create singleton limit instance"""
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class Budget(models.Model):
    """
    UC-011: Budget Management
    Enhanced budget entity with reallocation tracking and utilization monitoring
    
    Categories: manpower, travel, consumables, equipment, contingency, overhead
    Each stored as nested dict with budget amounts
    
    BR-RSPC-08: Max 20% reallocation per category per year
    BR-RSPC-11: Only RSPC Admin can update utilized amounts
    """
    bid = models.AutoField(primary_key=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='budget')
    
    # Budget categories - each as nested dict with year-wise allocations
    manpower = models.JSONField(default=dict, help_text="Year-wise manpower budget")
    travel = models.JSONField(default=dict, help_text="Year-wise travel budget")
    consumables = models.JSONField(default=dict, help_text="Year-wise consumables budget")
    equipment = models.JSONField(default=dict, help_text="Year-wise equipment budget")
    contingency = models.JSONField(default=dict, help_text="Year-wise contingency budget")
    overhead = models.JSONField(default=dict, help_text="Year-wise overhead budget/percentage")
    
    # Financial tracking
    total_sanctioned = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_funds = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Utilization tracking (JSONField for flexibility)
    utilized_amounts = models.JSONField(
        default=dict,
        help_text="Per-category utilization tracking with timestamps"
    )
    
    # Metadata
    last_modified = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_by = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        db_table = 'budget'
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'

    def __str__(self):
        return f"Budget for Project {self.project.name} (₹{self.total_sanctioned})"
    
    def get_total_budget(self):
        """Calculate total budget from all categories"""
        from decimal import Decimal
        total = Decimal('0')
        for category in ['manpower', 'travel', 'consumables', 'equipment', 'contingency']:
            cat_data = getattr(self, category, {})
            if isinstance(cat_data, dict):
                for year_amount in cat_data.values():
                    if isinstance(year_amount, (int, float)):
                        total += Decimal(str(year_amount))
        return total
    
    def get_category_utilization(self, category):
        """Get utilization for a specific category"""
        if not self.utilized_amounts:
            return Decimal('0')
        cat_util = self.utilized_amounts.get(category, {})
        if isinstance(cat_util, dict):
            return sum(Decimal(str(v)) for v in cat_util.values() if isinstance(v, (int, float)))
        return Decimal('0')
    
    def get_utilization_percentage(self):
        """Calculate overall budget utilization percentage"""
        if self.total_sanctioned <= 0:
            return 0
        return (float(self.current_funds) / float(self.total_sanctioned)) * 100
    
    def get_category_budget(self, category):
        """Get total budget allocated for a category across all years"""
        from decimal import Decimal
        cat_data = getattr(self, category, {}) or {}
        if isinstance(cat_data, dict):
            return sum(Decimal(str(v)) for v in cat_data.values() if isinstance(v, (int, float, Decimal)))
        return Decimal('0')


class BudgetReallocation(models.Model):
    """
    Budget reallocation request tracking (UC-011)
    
    Tracks all budget reallocation requests with:
    - Source and target categories
    - Amount and justification
    - Approval status
    - Enforcement of BR-RSPC-08 (20% max reallocation per category per year)
    """
    REALLOCATION_STATUS_CHOICES = (
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('IMPLEMENTED', 'Implemented'),
    )
    
    rbid = models.AutoField(primary_key=True)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='reallocations')
    
    # Reallocation details
    from_category = models.CharField(max_length=50, choices=ExpenditureHead.choices)
    to_category = models.CharField(max_length=50, choices=ExpenditureHead.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    financial_year = models.CharField(max_length=10, help_text="e.g., 2023-24")
    
    # Justification & approval
    justification = models.TextField()
    requires_approval = models.BooleanField(
        default=False,
        help_text="True if reallocation exceeds 20% limit (BR-RSPC-08)"
    )
    approval_status = models.CharField(
        max_length=20,
        choices=REALLOCATION_STATUS_CHOICES,
        default='REQUESTED'
    )
    approved_by = models.CharField(max_length=150, null=True, blank=True)
    approval_comments = models.TextField(null=True, blank=True)
    
    # Metadata
    requested_by = models.CharField(max_length=150)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    implemented_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rspc_budget_reallocation'
        verbose_name = 'Budget Reallocation'
        verbose_name_plural = 'Budget Reallocations'

    def __str__(self):
        return f"Reallocation: {self.from_category}→{self.to_category} (₹{self.amount})"


class BudgetModificationHistory(models.Model):
    """
    Budget modification audit trail (UC-011 requirement)
    
    Tracks all modifications with:
    - Timestamp and user
    - Change details (what changed, from value to value)
    - Reason/justification
    """
    MODIFICATION_TYPE_CHOICES = (
        ('INITIAL', 'Initial Budget'),
        ('REALLOCATION', 'Reallocation'),
        ('UTILIZATION_UPDATE', 'Utilization Update'),
        ('SANCTION_UPDATE', 'Sanction Amount Update'),
    )
    
    hmid = models.AutoField(primary_key=True)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='modification_history')
    
    # Modification details
    modification_type = models.CharField(max_length=50, choices=MODIFICATION_TYPE_CHOICES)
    category = models.CharField(max_length=50, choices=ExpenditureHead.choices, null=True, blank=True)
    
    # Change tracking
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    change_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Metadata
    reason = models.TextField()
    modified_by = models.CharField(max_length=150)
    modified_at = models.DateTimeField(auto_now_add=True)
    related_reallocation = models.ForeignKey(
        BudgetReallocation, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        db_table = 'rspc_budget_modification_history'
        verbose_name = 'Budget Modification History'
        verbose_name_plural = 'Budget Modification Histories'
        ordering = ['-modified_at']

    def __str__(self):
        return f"{self.modification_type} on {self.modified_at.strftime('%Y-%m-%d %H:%M')}"


class Staff(models.Model):
    """
    Staff entity (from views.py analysis)
    Maps to 'staff' table in database
    """
    sid = models.AutoField(primary_key=True)
    pid = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='pid')
    person = models.CharField(max_length=200)
    uname = models.CharField(max_length=100)  # Username
    biodata_number = models.CharField(max_length=50)
    start_date = models.DateTimeField()
    duration = models.IntegerField()  # In months
    eligibility = models.TextField()
    type = models.CharField(max_length=50, choices=StaffType.choices)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    has_funds = models.BooleanField(default=False)
    post_on_website = models.BooleanField(default=False)
    submission_date = models.DateTimeField(null=True, blank=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    test_date = models.DateTimeField(null=True, blank=True)
    test_mode = models.CharField(max_length=50, blank=True)
    interview_place = models.CharField(max_length=200, blank=True)
    selection_committee = models.JSONField(default=list)
    candidates_applied = models.IntegerField(default=0)
    candidates_called = models.IntegerField(default=0)
    candidates_interviewed = models.IntegerField(default=0)
    final_selection = models.JSONField(default=list)
    waiting_list = models.JSONField(default=list)
    biodata_final = models.JSONField(default=list)
    biodata_waiting = models.JSONField(default=list)
    ad_file = models.FileField(upload_to='rspc/staff/ad/', null=True, blank=True)
    comparative_file = models.FileField(upload_to='rspc/staff/comparative/', null=True, blank=True)
    approval = models.JSONField(default=dict)
    gave_verdict = models.JSONField(default=dict)
    current_approver = models.CharField(max_length=100, blank=True)
    joining_report = models.FileField(upload_to='rspc/staff/joining/', null=True, blank=True)
    doc_approval = models.BooleanField(default=False)
    salary_per_month = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    id_card = models.FileField(upload_to='rspc/staff/id_cards/', null=True, blank=True)
    approval_status = models.CharField(max_length=50, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_created')
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    no_of_positions = models.IntegerField(default=1, help_text="Number of positions to fill")
    qualification = models.TextField(blank=True, help_text="Required qualifications")
    experience = models.IntegerField(default=0, help_text="Required years of experience")
    approval_chain = models.JSONField(default=dict, help_text="Tracks approval history at each stage")
    
    # BR-018: Approval SLA fields (7 day deadline for staff)
    approval_deadline = models.DateTimeField(null=True, blank=True, help_text="Approval deadline (7 days from submission)")
    approval_status_escalated = models.BooleanField(default=False, help_text="BR-018: Has approval been escalated?")
    escalation_date = models.DateTimeField(null=True, blank=True, help_text="When approval was escalated")

    class Meta:
        db_table = 'staff'
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['pid', 'approval_status']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.sid} - {self.person}"
    
    def get_approval_status_display(self):
        """Get human-readable approval status"""
        return dict(StaffApprovalStatus.choices).get(self.approval_status, self.approval_status)
    
    def can_transition_to(self, target_status: str) -> Tuple[bool, str]:
        """Check if status transition is valid (BR-RSPC-12 validation)"""
        valid_transitions = {
            'DRAFT': ['COMMITTEE_PENDING', 'REJECTED'],
            'COMMITTEE_PENDING': ['COMMITTEE_APPROVED', 'COMMITTEE_REJECTED', 'REJECTED'],
            'COMMITTEE_APPROVED': ['HOD_PENDING', 'REJECTED'],
            'COMMITTEE_REJECTED': ['REJECTED'],
            'HOD_PENDING': ['HOD_APPROVED', 'HOD_REJECTED', 'REJECTED'],
            'HOD_APPROVED': ['RSPC_PENDING', 'REJECTED'],
            'HOD_REJECTED': ['REJECTED'],
            'RSPC_PENDING': ['RSPC_APPROVED', 'RSPC_REJECTED', 'APPOINTED'],
            'RSPC_APPROVED': ['APPOINTED', 'REJECTED'],
            'RSPC_REJECTED': ['REJECTED'],
            'APPOINTED': ['REJECTED'],  # Can only be rejected after appointment
        }
        
        if self.approval_status not in valid_transitions:
            return False, f"Invalid current status: {self.approval_status}"
        
        if target_status not in valid_transitions[self.approval_status]:
            return False, f"Cannot transition from {self.approval_status} to {target_status}"
        
        return True, "Valid transition"
    
    def get_committee(self):
        """Get the associated committee if exists"""
        return Committee.objects.filter(staff=self).first()
    
    def all_committee_verdicts_submitted(self) -> bool:
        """Check if all committee members have submitted verdicts (UC-008)"""
        committee = self.get_committee()
        if not committee:
            return False
        
        total_members = committee.members.count()
        submitted_verdicts = CommitteeVerdict.objects.filter(
            committee=committee,
            decision__isnull=False
        ).exclude(has_conflict_of_interest=True).count()
        
        return total_members == submitted_verdicts


class StaffPosition(models.Model):
    """
    Staff positions entity (from views.py analysis)
    Maps to 'staff_positions' table in database
    """
    spid = models.AutoField(primary_key=True)
    pid = models.OneToOneField(Project, on_delete=models.CASCADE, db_column='pid')
    positions = models.JSONField(default=dict)  # Available positions
    incumbents = models.JSONField(default=dict)  # Current incumbents
    vacancy = models.IntegerField(default=0)

    class Meta:
        db_table = 'staff_positions'
        verbose_name = 'Staff Position'
        verbose_name_plural = 'Staff Positions'

    def __str__(self):
        return f"Staff Positions for Project {self.pid_id}"


class ProjectAccess(models.Model):
    """
    Project access for Co-PIs (from views.py analysis)
    Maps to 'co_pis' or 'project_access' table in database
    """
    aid = models.AutoField(primary_key=True)
    pid = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='pid')
    type = models.CharField(max_length=50)  # internal/external
    copi_id = models.CharField(max_length=100)
    affiliation = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'co_pis'
        verbose_name = 'Project Access'
        verbose_name_plural = 'Project Accesses'
        unique_together = ('pid', 'copi_id')  # BR-RSPC-21: No duplicate Co-PIs

    def __str__(self):
        return f"Access for {self.copi_id} to Project {self.pid_id}"


class CoPI(models.Model):
    """
    Co-Investigator entity
    """
    copi_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=50)  # internal/external
    affiliation = models.CharField(max_length=200, blank=True)
    username = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        db_table = 'rspc_copi'
        verbose_name = 'Co-Investigator'
        verbose_name_plural = 'Co-Investigators'

    def __str__(self):
        return f"{self.name} ({self.type})"


class FinancialOutlay(models.Model):
    """
    Financial outlay entity (from views.py analysis)
    Maps to 'financial_outlay' table in database
    """
    financial_outlay_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='project_id')
    category = models.CharField(max_length=100)
    sub_category = models.CharField(max_length=100)
    year = models.IntegerField()
    allotted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    utilized_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'financial_outlay'
        verbose_name = 'Financial Outlay'
        verbose_name_plural = 'Financial Outlays'
        unique_together = ('project', 'category', 'sub_category', 'year')

    def __str__(self):
        return f"{self.project_id} - {self.category} - Year {self.year}"


class StaffAllocation(models.Model):
    """
    Staff allocation entity (from views.py analysis)
    Maps to 'staff_allocations' table in database
    """
    allocation_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='project_id')
    staff_id = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    qualification = models.CharField(max_length=200)
    stipend = models.DecimalField(max_digits=10, decimal_places=2)
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = 'staff_allocations'
        verbose_name = 'Staff Allocation'
        verbose_name_plural = 'Staff Allocations'

    def __str__(self):
        return f"{self.staff_id} - Project {self.project_id} - Year {self.year}"


class Request(models.Model):
    """
    Request entity (from views.py analysis)
    Maps to 'requests' table in database
    """
    request_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='project_id')
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=50, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'requests'
        verbose_name = 'Request'
        verbose_name_plural = 'Requests'

    def __str__(self):
        return f"{self.request_id} - {self.request_type} - {self.project_id}"


class RSPCInventory(models.Model):
    """
    RSPC Inventory entity (from views.py analysis)
    Maps to 'rspc_inventory' table in database
    """
    request_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='project_id')
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=50, default='PENDING')

    class Meta:
        db_table = 'rspc_inventory'
        verbose_name = 'RSPC Inventory'
        verbose_name_plural = 'RSPC Inventories'

    def __str__(self):
        return f"Inventory {self.request_id} - Project {self.project_id}"


class File(models.Model):
    """
    File entity (from views.py analysis)
    Maps to 'file' table in database
    """
    id = models.AutoField(primary_key=True)
    uploader = models.CharField(max_length=100)
    uploader_design = models.CharField(max_length=100)
    receiver = models.CharField(max_length=100)
    receiver_design = models.CharField(max_length=100)
    src_module = models.CharField(max_length=100)
    src_object_id = models.CharField(max_length=100)
    subject = models.CharField(max_length=500)
    attachment = models.FileField(upload_to='rspc/files/')
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'file'
        verbose_name = 'File'
        verbose_name_plural = 'Files'

    def __str__(self):
        return f"File {self.id} - {self.subject}"


class Tracking(models.Model):
    """
    Tracking entity (from views.py analysis)
    Maps to 'tracking' table in database
    """
    id = models.AutoField(primary_key=True)
    file = models.ForeignKey(File, on_delete=models.CASCADE, db_column='file_id')
    sender_id = models.CharField(max_length=100)
    sender_design = models.CharField(max_length=100)
    receiver_id = models.CharField(max_length=100)
    receive_design = models.CharField(max_length=100)
    receive_date = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)
    attachment = models.FileField(upload_to='rspc/tracking/', null=True, blank=True)
    current_id = models.CharField(max_length=100, blank=True)  # Current holder
    src_module = models.CharField(max_length=100, default='research_procedures')

    class Meta:
        db_table = 'tracking'
        verbose_name = 'Tracking'
        verbose_name_plural = 'Trackings'

    def __str__(self):
        return f"Tracking {self.id} - File {self.file_id}"


class Committee(models.Model):
    """
    Committee entity (from views.py analysis)
    """
    committee_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(ExtraInfo, related_name='committees')
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'rspc_committee'
        verbose_name = 'Committee'
        verbose_name_plural = 'Committees'

    def __str__(self):
        return f"Committee {self.committee_id} - {self.name}"


class CommitteeVerdict(models.Model):
    """
    Committee verdict entity (from views.py analysis)
    """
    verdict_id = models.AutoField(primary_key=True)
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name='verdicts')
    member = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE, related_name='verdicts')
    decision = models.CharField(max_length=20, choices=CommitteeDecision.choices, null=True, blank=True)
    comments = models.TextField(blank=True)
    has_conflict_of_interest = models.BooleanField(default=False, help_text="BR-RSPC-15: Conflict of interest")
    conflict_reason = models.TextField(blank=True, help_text="Reason for conflict if applicable")
    submitted_date = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rspc_committee_verdict'
        verbose_name = 'Committee Verdict'
        verbose_name_plural = 'Committee Verdicts'
        unique_together = ('committee', 'member')

    def __str__(self):
        return f"Verdict {self.verdict_id} - {self.member} - {self.decision}"


class CommitteeMember(models.Model):
    """
    Explicit tracking of committee members with appointed date (UC-026, BR-RSPC-12)
    Ensures all members are PI-eligible (Professor/Assoc/Asst Prof)
    """
    id = models.AutoField(primary_key=True)
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name='committee_members')
    member = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE, related_name='committee_appointments')
    appointed_date = models.DateTimeField(auto_now_add=True)
    is_pi_eligible = models.BooleanField(
        default=False,
        help_text="BR-RSPC-12: Must be Professor/Assoc/Asst Prof"
    )
    designation = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'rspc_committee_member'
        verbose_name = 'Committee Member'
        verbose_name_plural = 'Committee Members'
        unique_together = ('committee', 'member')
    
    def __str__(self):
        return f"Committee {self.committee_id} - Member {self.member}"


# ============================================================================
# EXPENDITURE MANAGEMENT MODELS (UC-012, UC-013, BR-RSPC-13)
# ============================================================================

class ExpenditureStatus(models.TextChoices):
    """Expenditure approval status (BR-RSPC-13)"""
    PENDING = 'PENDING', 'Pending'
    PI_APPROVED = 'PI_APPROVED', 'PI Approved'
    HOD_APPROVED = 'HOD_APPROVED', 'HOD Approved'
    RSPC_APPROVED = 'RSPC_APPROVED', 'RSPC Admin Approved'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class ApprovalStage(models.IntegerChoices):
    """Current approval stage (BR-RSPC-13)"""
    PI = 0, 'PI Approval'
    HOD = 1, 'HOD Approval'
    RSPC = 2, 'RSPC Admin Approval'


class CurrentApprover(models.TextChoices):
    """Current approver role"""
    PI = 'PI', 'Principal Investigator'
    HOD = 'HOD', 'Head of Department'
    RSPC = 'RSPC', 'RSPC Administrator'


class Expenditure(models.Model):
    """
    Expenditure request with 3-tier approval chain (UC-012, UC-013, BR-RSPC-13)
    
    Approval routing based on amount:
    - Level 1 (≤₹50K): PI approves only
    - Level 2 (₹50K-₹200K): PI → HOD
    - Level 3 (>₹200K): PI → HOD → RSPC Admin
    """
    eid = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenditures')
    
    # Expenditure details
    category = models.CharField(max_length=20, choices=ExpenditureHead.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    purpose = models.TextField(validators=[MinValueValidator(20)])  # Minimum 20 chars
    
    # Status tracking
    status = models.CharField(max_length=20, choices=ExpenditureStatus.choices, default=ExpenditureStatus.PENDING)
    current_stage = models.IntegerField(choices=ApprovalStage.choices, default=ApprovalStage.PI)
    current_approver = models.CharField(max_length=10, choices=CurrentApprover.choices, default=CurrentApprover.PI)
    
    # Request info
    requested_by = models.ForeignKey(ExtraInfo, on_delete=models.SET_NULL, null=True, related_name='expenditures_created')
    # DB column is `requested_at`; keep Python attribute `request_date` for backward compatibility.
    request_date = models.DateTimeField(auto_now_add=True, db_column='requested_at')
    
     # Approval chain tracking (JSONField stores all approvals)
    approval_chain = models.JSONField(
        default=dict,
        help_text="Tracks approval history: {stage: {approver, approved_at, comments}}"
    )
    
    # Documents
    supporting_documents = models.JSONField(default=list, help_text="List of document file paths")
    
    # BR-018: Approval SLA fields
    approval_deadline = models.DateTimeField(null=True, blank=True, help_text="Deadline based on amount tier")
    approval_status_escalated = models.BooleanField(default=False, help_text="BR-018: Has approval been escalated?")
    escalation_date = models.DateTimeField(null=True, blank=True, help_text="When approval was escalated")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rspc_expenditure'
        verbose_name = 'Expenditure'
        verbose_name_plural = 'Expenditures'
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['current_approver', 'status']),
            models.Index(fields=['amount', 'status']),
        ]

    def __str__(self):
        return f"Expenditure {self.eid} - {self.category} - ₹{self.amount}"
    
    def get_approval_tier(self):
        """Determine approval tier based on amount (BR-RSPC-13)"""
        if self.amount <= 50000:
            return 1  # Level 1: PI only
        elif self.amount <= 200000:
            return 2  # Level 2: PI + HOD
        else:
            return 3  # Level 3: PI + HOD + RSPC
    
    def get_next_approver_role(self):
        """Get next approver role in chain"""
        tier = self.get_approval_tier()
        if tier == 1:
            return None  # No more approvers after PI
        elif tier == 2:
            if self.current_stage == ApprovalStage.PI:
                return CurrentApprover.HOD
            return None
        else:  # tier == 3
            if self.current_stage == ApprovalStage.PI:
                return CurrentApprover.HOD
            elif self.current_stage == ApprovalStage.HOD:
                return CurrentApprover.RSPC
            return None


class ExpenditureApprovalHistory(models.Model):
    """
    Audit trail for all expenditure approvals (UC-012 requirement)
    
    Tracks:
    - Who approved/rejected and when
    - Comments/reasons
    - Stage in approval chain
    """
    ahid = models.AutoField(primary_key=True)
    expenditure = models.ForeignKey(Expenditure, on_delete=models.CASCADE, related_name='approval_history')
    
    # Approval details
    approver = models.ForeignKey(ExtraInfo, on_delete=models.SET_NULL, null=True, related_name='approved_expenditures')
    approver_role = models.CharField(max_length=10, choices=CurrentApprover.choices)
    action = models.CharField(max_length=20, choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected')])
    
    # Comments
    comments = models.TextField(blank=True)
    
    # Metadata
    approved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rspc_expenditure_approval_history'
        verbose_name = 'Expenditure Approval History'
        verbose_name_plural = 'Expenditure Approval Histories'
        ordering = ['-approved_at']

    def __str__(self):
        return f"{self.expenditure.eid} - {self.approver_role} {self.action}"


# ============================================================================
# NOTIFICATION EVENT TYPES (UC-015)
# ============================================================================

class NotificationEventType(models.TextChoices):
    """14 Event types for notifications system (UC-015)"""
    # Expenditure events (3 types)
    EXPENDITURE_PENDING_APPROVAL = 'expenditure_pending_approval', 'Expenditure Pending Approval'
    EXPENDITURE_APPROVED = 'expenditure_approved', 'Expenditure Approved'
    EXPENDITURE_REJECTED = 'expenditure_rejected', 'Expenditure Rejected'
    
    # Budget events (1 type)
    BUDGET_REALLOCATED = 'budget_reallocated', 'Budget Reallocated'
    
    # Proposal/Project events (3 types)
    PROPOSAL_PENDING_VERIFICATION = 'proposal_pending_verification', 'Proposal Pending Verification'
    PROPOSAL_APPROVED = 'proposal_approved', 'Proposal Approved'
    PROPOSAL_REJECTED = 'proposal_rejected', 'Proposal Rejected'
    
    # Staff events (4 types)
    STAFF_COMMITTEE_PENDING = 'staff_committee_pending', 'Staff Committee Pending'
    STAFF_HOD_PENDING = 'staff_hod_pending', 'Staff HOD Pending'
    STAFF_RSPC_PENDING = 'staff_rspc_pending', 'Staff RSPC Pending'
    STAFF_APPOINTED = 'staff_appointed', 'Staff Appointed'
    
    # Fund events (2 types)
    FUND_REQUEST_PENDING = 'fund_request_pending', 'Fund Request Pending'
    FUND_APPROVED = 'fund_approved', 'Fund Approved'
    FUND_REJECTED = 'fund_rejected', 'Fund Rejected'
    
    # Patent events (1 type)
    PATENT_UPDATED = 'patent_updated', 'Patent Updated'
    
    # Small Fund Request events (3 types - UC-021, UC-022, UC-023)
    SMALL_FUND_SUBMITTED = 'small_fund_submitted', 'Small Fund Request Submitted'
    SMALL_FUND_APPROVED = 'small_fund_approved', 'Small Fund Request Approved'
    SMALL_FUND_REJECTED = 'small_fund_rejected', 'Small Fund Request Rejected'
    SMALL_FUND_DISBURSED = 'small_fund_disbursed', 'Small Fund Disbursed'


class NotificationEntityType(models.TextChoices):
    """Entity types for notifications"""
    EXPENDITURE = 'expenditure', 'Expenditure'
    PROJECT = 'project', 'Project'
    BUDGET = 'budget', 'Budget'
    STAFF = 'staff', 'Staff'
    FUND = 'fund', 'Fund'
    PATENT = 'patent', 'Patent'
    SMALL_FUND = 'small_fund', 'Small Fund Request'


# ============================================================================
# NOTIFICATION MODELS (UC-015 Implementation)
# ============================================================================

class Notification(models.Model):
    """
    Complete Notifications System for RSPC (UC-015)
    
    Tracks all system notifications with:
    - Sender and recipient users
    - Event type (one of 14 types)
    - Entity type and ID for linking to actual objects
    - Title and message with variable substitution
    - Read/unread status
    """
    nid = models.AutoField(primary_key=True)
    
    # Sender and recipient (User FKs)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_sent', null=True, blank=True)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_received')
    
    # Event type (one of 14 types)
    event_type = models.CharField(max_length=50, choices=NotificationEventType.choices)
    
    # Entity reference
    entity_type = models.CharField(max_length=50, choices=NotificationEntityType.choices)
    entity_id = models.CharField(max_length=100)  # Can be int or string
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_read = models.BooleanField(default=False)
    
    # Metadata for building action links
    context_data = models.JSONField(default=dict, help_text="Additional context for rendering")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rspc_notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"Notification {self.nid} - {self.event_type} for {self.recipient}"


# ============================================================================
# REPORT SCHEDULING MODELS (from PSM specification)
# ============================================================================

class ScheduledReport(models.Model):
    """
    Scheduled report entity (from PSM specification)
    """
    sid = models.AutoField(primary_key=True)
    report_type = models.CharField(max_length=100)
    frequency = models.CharField(max_length=50)  # Daily, Weekly, Monthly, Quarterly
    recipients = models.JSONField(default=list)
    next_run = models.DateTimeField()
    created_by = models.CharField(max_length=150)
    parameters = models.JSONField(default=dict)

    class Meta:
        db_table = 'rspc_scheduled_report'
        verbose_name = 'Scheduled Report'
        verbose_name_plural = 'Scheduled Reports'

    def __str__(self):
        return f"Scheduled Report {self.sid} - {self.report_type}"


# ============================================================================
# UC-006: PROGRESS REPORT MODELS
# ============================================================================

class ProgressReportStatus(models.TextChoices):
    """Progress report status choices (UC-006)"""
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    REVIEWED = 'REVIEWED', 'Reviewed'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class ProgressReportPeriod(models.TextChoices):
    """Report period types (BR-012)"""
    QUARTER = 'QUARTERLY', 'Quarterly'
    HALF_YEAR = 'HALF_YEARLY', 'Half Yearly'
    ANNUAL = 'ANNUAL', 'Annual'
    FINAL = 'FINAL', 'Final'


class ProgressReport(models.Model):
    """
    UC-006: Project Progress Report
    
    Tracks progress reports submitted by PIs with:
    - Project progress summary, challenges, milestones
    - Multiple periods (Quarterly, Half-yearly, Annual, Final)
    - Status workflow (Draft → Submitted → Reviewed → Approved/Rejected)
    - Enforces BR-012 (report frequency) and BR-013 (completeness)
    """
    prid = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_reports')
    
    # Report details
    report_period = models.CharField(max_length=20, choices=ProgressReportPeriod.choices)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='progress_reports_submitted')
    
    # Content
    report_content = models.TextField(help_text="Project progress summary")
    challenges_faced = models.TextField(help_text="Key challenges encountered")
    milestones_achieved = models.TextField(help_text="Milestones completed in this period")
    publications_filed = models.IntegerField(default=0, help_text="Number of publications")
    recommendations = models.TextField(blank=True, help_text="Future recommendations")
    
    # Files
    attachments = models.FileField(upload_to='rspc/reports/progress/', null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=ProgressReportStatus.choices, default=ProgressReportStatus.DRAFT)
    reviewer_comments = models.TextField(blank=True, help_text="Comments from RSPC Admin/Director")
    
    # Metadata
    submitted_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rspc_progress_report'
        verbose_name = 'Progress Report'
        verbose_name_plural = 'Progress Reports'
        ordering = ['-created_date']
        unique_together = ('project', 'report_period')  # BR-012: One report per period per project
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['submitted_by', '-created_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Progress Report {self.prid} - Project {self.project.pid} ({self.report_period})"


# ============================================================================
# UC-010: PROJECT CLOSURE REPORT MODELS
# ============================================================================

class ProjectClosureStatus(models.TextChoices):
    """Project closure status choices (UC-010)"""
    SUBMITTED = 'SUBMITTED', 'Submitted'
    VERIFIED = 'VERIFIED', 'Verified'
    SETTLED = 'SETTLED', 'Settled'
    CLOSED = 'CLOSED', 'Closed'


class ProjectClosure(models.Model):
    """
    UC-010: Project Closure Report
    
    Final project closure with:
    - Closure details (deliverables, challenges, lessons learned)
    - Publications and patents generated
    - Final settlement calculations (BR-015)
    - Status workflow (Submitted → Verified → Settled → Closed)
    - Enforces BR-014 (timeline validation) and BR-016 (document validation)
    """
    closure_id = models.AutoField(primary_key=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='closure_report')
    
    # Closure info
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='project_closures')
    
    # Content
    final_report = models.TextField(help_text="Final project report")
    deliverables_summary = models.TextField(help_text="Summary of deliverables")
    challenges_summary = models.TextField(help_text="Summary of challenges")
    lessons_learned = models.TextField(help_text="Lessons learned and recommendations")
    
    # Outputs
    publications_generated = models.IntegerField(default=0)
    patents_filed = models.IntegerField(default=0)
    utilization_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Files
    final_settlement_document = models.FileField(upload_to='rspc/closure/settlement/', null=True, blank=True)
    
    # Outstanding items
    outstanding_items = models.TextField(blank=True, help_text="Any outstanding items pending")
    
    # BR-015: Settlement calculations
    settlement_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Final settlement amount to be released")
    held_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Amount held if any")
    refund_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Unused funds to be refunded")
    penalty_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Penalties for timeline violations")
    settlement_calculated = models.BooleanField(default=False, help_text="BR-015: Has settlement been calculated?")
    settlement_approved = models.BooleanField(default=False, help_text="BR-015: Has settlement been approved by Director?")
    
    # Status
    status = models.CharField(max_length=20, choices=ProjectClosureStatus.choices, default=ProjectClosureStatus.SUBMITTED)
    
    # Metadata
    closure_date = models.DateTimeField(auto_now_add=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rspc_project_closure'
        verbose_name = 'Project Closure'
        verbose_name_plural = 'Project Closures'
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Closure {self.closure_id} - Project {self.project.pid} ({self.status})"


# ============================================================================
# BR-018: APPROVAL TIMEFRAME & SLA MODELS
# ============================================================================

class ApprovalSLAStatus(models.TextChoices):
    """SLA approval status"""
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    ESCALATED = 'ESCALATED', 'Escalated'
    TIMEOUT = 'TIMEOUT', 'Timeout'


class ApprovalSLAEntityType(models.TextChoices):
    """Types of entities requiring approval"""
    EXPENDITURE = 'expenditure', 'Expenditure'
    PROJECT = 'project', 'Project'
    STAFF = 'staff', 'Staff'
    PROGRESS_REPORT = 'progress_report', 'Progress Report'
    PROJECT_CLOSURE = 'project_closure', 'Project Closure'


class ApprovalSLA(models.Model):
    """
    BR-018: Approval SLA and Timeframe Tracking
    
    Tracks approval deadlines with:
    - Entity-specific timeframes (Tier-based for expenditure, 10 days for projects, 7 for staff)
    - Escalation levels (1=first, 2=second, 3=third)
    - Automatic escalation when deadline passes
    - Timeout notifications
    """
    sla_id = models.AutoField(primary_key=True)
    
    # Entity reference
    entity_type = models.CharField(max_length=20, choices=ApprovalSLAEntityType.choices)
    entity_id = models.CharField(max_length=100)  # Can be any entity ID
    
    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(help_text="Approval deadline based on BR-018")
    
    # Current approver
    current_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approvals_pending')
    
    # Escalation tracking
    escalation_level = models.IntegerField(default=1, choices=[(1, 'Level 1'), (2, 'Level 2'), (3, 'Level 3')])
    status = models.CharField(max_length=20, choices=ApprovalSLAStatus.choices, default=ApprovalSLAStatus.PENDING)
    
    # Notifications
    timeout_notified = models.BooleanField(default=False, help_text="Has timeout notification been sent?")
    escalation_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rspc_approval_sla'
        verbose_name = 'Approval SLA'
        verbose_name_plural = 'Approval SLAs'
        ordering = ['deadline']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['status', 'deadline']),
            models.Index(fields=['current_approver', 'status']),
        ]
    
    def __str__(self):
        return f"SLA {self.sla_id} - {self.entity_type} {self.entity_id} (Level {self.escalation_level})"


# ============================================================================
# UC-017: STIPEND DISBURSEMENT MODELS
# ============================================================================

class StipendDisbursementStatus(models.TextChoices):
    """Stipend disbursement status (UC-017)"""
    PENDING = 'PENDING', 'Pending'
    DISBURSED = 'DISBURSED', 'Disbursed'
    FAILED = 'FAILED', 'Failed'
    HOLD = 'HOLD', 'On Hold'


class PaymentMethod(models.TextChoices):
    """Payment method choices (UC-017)"""
    BANK = 'BANK', 'Bank Transfer'
    CHECK = 'CHECK', 'Check'
    CASH = 'CASH', 'Cash'


class StipendDisbursement(models.Model):
    """
    UC-017: Stipend Disbursement Record
    
    Individual staff stipend records with:
    - Staff and project assignment
    - Monthly allocation
    - Payment tracking (method, reference, status)
    - Audit trail (creation and modification dates)
    """
    id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='stipend_disbursements')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='staff_stipends')
    month = models.DateField(help_text="Start of month for stipend")
    stipend_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="BR-009: Within approved limits")
    status = models.CharField(
        max_length=20,
        choices=StipendDisbursementStatus.choices,
        default=StipendDisbursementStatus.PENDING
    )
    disbursement_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Bank ref/check no")
    remarks = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rspc_stipend_disbursement'
        verbose_name = 'Stipend Disbursement'
        verbose_name_plural = 'Stipend Disbursements'
        ordering = ['-month']
        unique_together = ('staff', 'project', 'month')  # Prevent duplicate records
        indexes = [
            models.Index(fields=['project', 'month']),
            models.Index(fields=['staff', '-month']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Stipend {self.id} - {self.staff.person} ({self.month.strftime('%Y-%m')})"


class StipendBatchStatus(models.TextChoices):
    """Stipend batch status (UC-017)"""
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    DISBURSED = 'DISBURSED', 'Disbursed'
    FAILED = 'FAILED', 'Failed'


class StipendBatch(models.Model):
    """
    UC-017: Stipend Disbursement Batch
    
    Batch of disbursement records for a project/month with:
    - Auto-calculated total amount
    - Approval workflow (PENDING → APPROVED → DISBURSED)
    - Disbursement count tracking
    - Approval metadata (who approved, when)
    """
    id = models.AutoField(primary_key=True)
    batch_date = models.DateField(auto_now_add=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stipend_batches')
    month = models.DateField(help_text="Month of stipend allocation")
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Auto-calculated")
    status = models.CharField(
        max_length=20,
        choices=StipendBatchStatus.choices,
        default=StipendBatchStatus.PENDING
    )
    disbursement_count = models.IntegerField(default=0)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_stipend_batches')
    approval_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rspc_stipend_batch'
        verbose_name = 'Stipend Batch'
        verbose_name_plural = 'Stipend Batches'
        ordering = ['-month']
        unique_together = ('project', 'month')  # Only one batch per project/month
        indexes = [
            models.Index(fields=['project', 'month']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Batch {self.id} - Project {self.project.pid} ({self.month.strftime('%Y-%m')})"


# ============================================================================
# UC-018: COMPLIANCE REPORT MODELS
# ============================================================================

class ComplianceReportType(models.TextChoices):
    """Report types for compliance (UC-018)"""
    BUDGET = 'BUDGET', 'Budget Compliance'
    EXPENDITURE = 'EXPENDITURE', 'Expenditure Compliance'
    STAFF = 'STAFF', 'Staff Compliance'
    PROJECT = 'PROJECT', 'Project Compliance'
    FULL = 'FULL', 'Full Compliance'


class ComplianceReportStatus(models.TextChoices):
    """Compliance report status (UC-018)"""
    GENERATED = 'GENERATED', 'Generated'
    REVIEWED = 'REVIEWED', 'Reviewed'
    APPROVED = 'APPROVED', 'Approved'
    PUBLISHED = 'PUBLISHED', 'Published'


class ComplianceReport(models.Model):
    """
    UC-018: Compliance Report
    
    Comprehensive compliance audit with:
    - Report generation (type-based data collection)
    - Validation against BR rules
    - Compliance scoring (% compliant)
    - Multi-format export (PDF, Excel)
    - Approval workflow
    """
    id = models.AutoField(primary_key=True)
    report_date = models.DateField(auto_now_add=True)
    report_type = models.CharField(max_length=20, choices=ComplianceReportType.choices)
    period_start = models.DateField(help_text="Report period start")
    period_end = models.DateField(help_text="Report period end")
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_compliance_reports')
    status = models.CharField(
        max_length=20,
        choices=ComplianceReportStatus.choices,
        default=ComplianceReportStatus.GENERATED
    )
    total_items_checked = models.IntegerField(default=0)
    compliant_items = models.IntegerField(default=0)
    non_compliant_items = models.IntegerField(default=0)
    compliance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    report_content = models.JSONField(default=dict, help_text="Structured compliance data")
    export_formats = models.JSONField(default=dict, help_text="PDF/Excel file paths")
    notes = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rspc_compliance_report'
        verbose_name = 'Compliance Report'
        verbose_name_plural = 'Compliance Reports'
        ordering = ['-report_date']
        indexes = [
            models.Index(fields=['report_type', '-report_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"ComplianceReport {self.id} - {self.report_type} ({self.report_date})"


# ============================================================================
# UC-004: PROJECT VERSION HISTORY MODELS
# ============================================================================

class ProjectVersion(models.Model):
    """
    UC-004: Project version history for tracking updates
    
    Maintains audit trail of project modifications with:
    - Version number (auto-incremented per project)
    - Captured values (title, description, budget)
    - Change metadata (who, when, why)
    - Change type classification
    """
    pvid = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='versions')
    
    # Version tracking
    version_number = models.IntegerField(help_text="Auto-increment per project")
    
    # Captured state
    title = models.CharField(max_length=200)
    description = models.TextField()
    budget = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Change metadata
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='project_version_changes')
    changed_date = models.DateTimeField(auto_now_add=True)
    change_reason = models.CharField(max_length=200)
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    
    class Meta:
        db_table = 'rspc_project_version'
        verbose_name = 'Project Version'
        verbose_name_plural = 'Project Versions'
        ordering = ['-version_number']
        unique_together = ('project', 'version_number')
    
    def __str__(self):
        return f"Project {self.project.pid} - Version {self.version_number}"


# ============================================================================
# UC-005: PROJECT CANCELLATION MODELS
# ============================================================================

class CancellationRequest(models.Model):
    """
    UC-005: Project cancellation request workflow
    
    Optional model for formal cancellation requests:
    - PI requests cancellation
    - RSPC Admin must approve
    - Tracks approval status
    """
    crid = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='cancellation_requests')
    
    # Request details
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cancellation_requests_submitted')
    reason = models.TextField(help_text="Cancellation reason")
    
    # Approval
    approval_status = models.CharField(max_length=20, choices=CancellationRequestStatus.choices, default=CancellationRequestStatus.PENDING)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancellation_requests_approved')
    approval_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rspc_cancellation_request'
        verbose_name = 'Cancellation Request'
        verbose_name_plural = 'Cancellation Requests'
        ordering = ['-created_date']
    
    def __str__(self):
        return f"Cancellation Request {self.crid} - Project {self.project.pid}"


# ============================================================================
# UC-012: PROPOSAL VETTING MODELS
# ============================================================================

class ProposalVetting(models.Model):
    """
    UC-012: HOD proposal vetting for academic soundness
    
    Tracks HOD evaluation of proposals:
    - Multiple criteria (feasibility, relevance, resources, alignment)
    - Pass/Fail/Flag outcome for each
    - Overall vetting decision
    - Audit trail
    
    BR-RSPC-10: HOD vetting required before Director review
    """
    vetting_id = models.AutoField(primary_key=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='proposal_vetting')
    
    # Vetter info
    vetted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='proposals_vetted')
    
    # Vetting criteria
    technical_feasibility = models.CharField(max_length=10, choices=VettingStatus.choices, help_text="Can it be technically achieved?")
    academic_relevance = models.CharField(max_length=10, choices=VettingStatus.choices, help_text="Is it academically sound?")
    resource_adequacy = models.CharField(max_length=10, choices=VettingStatus.choices, help_text="Are resources adequate?")
    department_alignment = models.CharField(max_length=10, choices=VettingStatus.choices, help_text="Does it align with department?")
    
    # Comments and decision
    comments = models.TextField(blank=True, help_text="Vetting comments and feedback")
    status = models.CharField(max_length=20, choices=ProposalVettingStatus.choices, default=ProposalVettingStatus.PENDING)
    
    # Timestamps
    vetting_date = models.DateTimeField(auto_now_add=True)
    vetting_completed_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'rspc_proposal_vetting'
        verbose_name = 'Proposal Vetting'
        verbose_name_plural = 'Proposal Vettings'
    
    def __str__(self):
        return f"Vetting {self.vetting_id} - Project {self.project.pid} ({self.status})"


# ============================================================================
# BR-015: FINAL SETTLEMENT ENHANCEMENTS
# ============================================================================

# Update ProjectClosure model fields via migration
# Adding fields:
# - settlement_amount (DecimalField)
# - held_amount (DecimalField)
# - refund_amount (DecimalField)
# - penalty_amount (DecimalField)
# - settlement_calculated (BooleanField)
# - settlement_approved (BooleanField)

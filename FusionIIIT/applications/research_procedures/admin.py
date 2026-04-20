"""
RSPC Module - Django Admin Registration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    # Research Areas
    ResearchGroup, ResearchArea,
    
    # Sponsored Projects
    FundingAgency, SponsoredProject, ProjectExpenditure,
    ProjectMilestone, ProjectReport,
    
    # Consultancy
    ConsultancyProject,
    
    # Publications & Patents
    Publication, Patent,
    
    # Research Scholars
    ResearchScholar,
    
    # Core Tables (from views.py analysis)
    Project, Budget, Staff, StaffPosition,
    ProjectAccess, FinancialOutlay, StaffAllocation,
    Request, RSPCInventory, Tracking, File,
    Committee, CommitteeVerdict, CoPI,
    ResearchGroup as ResearchGroupModel,
    
    # UC-006, UC-010, BR-018 new models
    ProgressReport, ProjectClosure, ApprovalSLA
)


# ============================================================================
# RESEARCH AREAS ADMIN
# ============================================================================

@admin.register(ResearchGroup)
class ResearchGroupAdmin(admin.ModelAdmin):
    """Admin for Research Groups"""
    list_display = ('name', 'acronym', 'discipline', 'head', 'is_active')
    list_filter = ('discipline', 'is_active')
    search_fields = ('name', 'acronym', 'description')
    filter_horizontal = ('members',)
    readonly_fields = ('established_date',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'acronym', 'discipline', 'description')
        }),
        ('Leadership', {
            'fields': ('head', 'members')
        }),
        ('Additional Info', {
            'fields': ('established_date', 'website', 'is_active')
        }),
    )


@admin.register(ResearchArea)
class ResearchAreaAdmin(admin.ModelAdmin):
    """Admin for Research Areas"""
    list_display = ('name', 'parent_area', 'discipline', 'is_active')
    list_filter = ('discipline', 'is_active')
    search_fields = ('name', 'description')
    filter_horizontal = ('faculty_experts',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'parent_area', 'discipline')
        }),
        ('Experts', {
            'fields': ('faculty_experts',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


# ============================================================================
# SPONSORED PROJECTS ADMIN
# ============================================================================

@admin.register(FundingAgency)
class FundingAgencyAdmin(admin.ModelAdmin):
    """Admin for Funding Agencies"""
    list_display = ('name', 'acronym', 'agency_type', 'country', 'is_active')
    list_filter = ('agency_type', 'country', 'is_active')
    search_fields = ('name', 'acronym', 'contact_info')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'acronym', 'agency_type', 'country')
        }),
        ('Contact', {
            'fields': ('website', 'contact_info')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(SponsoredProject)
class SponsoredProjectAdmin(admin.ModelAdmin):
    """Admin for Sponsored Projects"""
    list_display = ('project_number', 'title', 'principal_investigator', 
                   'funding_agency', 'sanctioned_amount', 'status')
    list_filter = ('status', 'research_area', 'funding_agency')
    search_fields = ('title', 'project_number', 'description')
    filter_horizontal = ('co_principal_investigators', 'research_scholars')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'project_number', 'description', 'research_area')
        }),
        ('Team', {
            'fields': ('principal_investigator', 'co_principal_investigators', 
                      'research_scholars')
        }),
        ('Funding', {
            'fields': ('funding_agency', 'sanctioned_amount', 'utilized_amount')
        }),
        ('Timeline', {
            'fields': ('submission_date', 'sanction_date', 'start_date',
                      'original_end_date', 'extended_end_date', 'actual_end_date')
        }),
        ('Status & Documents', {
            'fields': ('status', 'proposal_document', 'sanction_letter')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectExpenditure)
class ProjectExpenditureAdmin(admin.ModelAdmin):
    """Admin for Project Expenditures"""
    list_display = ('project', 'expenditure_head', 'amount', 'date', 'voucher_number')
    list_filter = ('expenditure_head', 'project')
    search_fields = ('description', 'voucher_number')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Expenditure Details', {
            'fields': ('project', 'expenditure_head', 'description', 'amount', 'date')
        }),
        ('Documentation', {
            'fields': ('voucher_number', 'bill_document', 'approved_by')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    """Admin for Project Milestones"""
    list_display = ('title', 'project', 'due_date', 'is_completed')
    list_filter = ('is_completed', 'project')
    search_fields = ('title', 'description')


@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    """Admin for Project Reports"""
    list_display = ('project', 'report_type', 'period_from', 'period_to', 'submitted_date', 'approved')
    list_filter = ('report_type', 'approved', 'project')
    search_fields = ('summary',)


# ============================================================================
# CONSULTANCY ADMIN
# ============================================================================

@admin.register(ConsultancyProject)
class ConsultancyProjectAdmin(admin.ModelAdmin):
    """Admin for Consultancy Projects"""
    list_display = ('project_number', 'title', 'consultant', 'client_name', 
                   'contract_amount', 'status')
    list_filter = ('status', 'client_type')
    search_fields = ('title', 'project_number', 'client_name', 'description')
    filter_horizontal = ('co_consultants',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'project_number', 'description')
        }),
        ('Client', {
            'fields': ('client_name', 'client_type', 'client_contact')
        }),
        ('Team', {
            'fields': ('consultant', 'co_consultants')
        }),
        ('Financial', {
            'fields': ('contract_amount', 'faculty_share', 'institute_share')
        }),
        ('Timeline & Status', {
            'fields': ('start_date', 'end_date', 'status')
        }),
        ('Documents', {
            'fields': ('agreement_document',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# PUBLICATIONS & PATENTS ADMIN
# ============================================================================

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    """Admin for Publications"""
    list_display = ('title', 'publication_type', 'year', 'journal_conference_name', 'is_verified')
    list_filter = ('publication_type', 'index_type', 'year', 'is_verified')
    search_fields = ('title', 'journal_conference_name', 'doi')
    filter_horizontal = ('faculty_authors', 'student_authors')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'publication_type')
        }),
        ('Authors', {
            'fields': ('faculty_authors', 'student_authors', 'external_authors')
        }),
        ('Publication Details', {
            'fields': ('journal_conference_name', 'publisher', 'volume', 'issue', 
                      'pages', 'year', 'month')
        }),
        ('Indexing', {
            'fields': ('index_type', 'impact_factor')
        }),
        ('Identifiers', {
            'fields': ('doi', 'issn', 'isbn', 'url')
        }),
        ('File & Verification', {
            'fields': ('pdf_file', 'is_verified', 'verified_by')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Patent)
class PatentAdmin(admin.ModelAdmin):
    """Admin for Patents"""
    list_display = ('title', 'patent_type', 'application_number', 'filing_date', 'status')
    list_filter = ('patent_type', 'status')
    search_fields = ('title', 'abstract', 'application_number', 'grant_number')
    filter_horizontal = ('faculty_inventors', 'student_inventors')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'abstract', 'patent_type')
        }),
        ('Inventors', {
            'fields': ('faculty_inventors', 'student_inventors', 'external_inventors')
        }),
        ('Filing Details', {
            'fields': ('application_number', 'filing_date', 'publication_number',
                      'publication_date', 'grant_number', 'grant_date')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Documents & Related', {
            'fields': ('specification_document', 'grant_certificate', 'related_project')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# RESEARCH SCHOLARS ADMIN
# ============================================================================

@admin.register(ResearchScholar)
class ResearchScholarAdmin(admin.ModelAdmin):
    """Admin for Research Scholars"""
    list_display = ('student', 'enrollment_date', 'expected_completion', 
                   'coursework_completed', 'thesis_submitted')
    list_filter = ('coursework_completed', 'comprehensive_exam_passed', 
                  'synopsis_submitted', 'thesis_submitted')
    search_fields = ('student__id__user__first_name', 'student__id__user__last_name')
    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Enrollment', {
            'fields': ('enrollment_date', 'expected_completion')
        }),
        ('Fellowship', {
            'fields': ('fellowship_type', 'fellowship_amount')
        }),
        ('Progress', {
            'fields': ('coursework_completed', 'comprehensive_exam_passed',
                      'comprehensive_exam_date')
        }),
        ('Thesis', {
            'fields': ('synopsis_submitted', 'synopsis_date', 'thesis_submitted',
                      'thesis_submission_date', 'defense_date', 'degree_awarded_date')
        }),
    )


# ============================================================================
# CORE PROJECT MANAGEMENT ADMIN (from views.py analysis)
# ============================================================================

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin for Core Projects"""
    list_display = ('pid', 'name', 'pi_name', 'status', 'sanctioned_amount', 'start_date')
    list_filter = ('status', 'type', 'category', 'dept')
    search_fields = ('name', 'pi_name', 'description')
    filter_horizontal = ()
    readonly_fields = ('pid',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'category', 'dept', 'description')
        }),
        ('Investigators', {
            'fields': ('pi_id', 'pi_name', 'access')
        }),
        ('Funding', {
            'fields': ('sponsored_agency', 'scheme', 'total_budget',
                      'sanctioned_amount', 'initial_amount')
        }),
        ('Timeline', {
            'fields': ('duration', 'submission_date', 'sanction_date',
                      'start_date', 'end_date')
        }),
        ('Status & Documents', {
            'fields': ('status', 'financial_outlay_status', 'file',
                      'registration_form', 'end_report', 'end_approval')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing existing object
            return ('pid',)
        return ()


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """Admin for Project Budgets"""
    list_display = ('bid', 'project', 'total_sanctioned', 'current_funds')
    search_fields = ('project__name',)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Admin for Staff"""
    list_display = ('sid', 'person', 'type', 'pid', 'salary', 'approval_status')
    list_filter = ('type', 'approval_status')
    search_fields = ('person', 'uname')


@admin.register(StaffAllocation)
class StaffAllocationAdmin(admin.ModelAdmin):
    """Admin for Staff Allocations"""
    list_display = ('allocation_id', 'staff_id', 'project', 'year', 'stipend')
    list_filter = ('year', 'project')
    search_fields = ('staff_id', 'name')


@admin.register(FinancialOutlay)
class FinancialOutlayAdmin(admin.ModelAdmin):
    """Admin for Financial Outlay"""
    list_display = ('financial_outlay_id', 'project', 'category', 'sub_category', 
                   'year', 'allotted_amount', 'utilized_amount')
    list_filter = ('category', 'sub_category', 'year', 'project')
    search_fields = ('project__name',)


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    """Admin for Requests (Funds/Staff)"""
    list_display = ('request_id', 'project', 'request_type', 'status')
    list_filter = ('request_type', 'status')
    search_fields = ('project__name',)


@admin.register(RSPCInventory)
class RSPCInventoryAdmin(admin.ModelAdmin):
    """Admin for RSPC Inventory (Fund Requests)"""
    list_display = ('request_id', 'project', 'amount', 'status')
    list_filter = ('status',)


@admin.register(Tracking)
class TrackingAdmin(admin.ModelAdmin):
    """Admin for File Tracking"""
    list_display = ('id', 'file_id', 'receiver_id', 'receive_design', 
                   'receive_date', 'current_id')
    list_filter = ('receive_design', 'src_module')
    search_fields = ('remarks',)


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """Admin for File Management"""
    list_display = ('id', 'uploader', 'uploader_design', 'receiver', 
                   'receiver_design', 'src_module', 'upload_date')
    list_filter = ('uploader_design', 'receiver_design', 'src_module')
    search_fields = ('subject',)


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    """Admin for Selection Committees"""
    list_display = ('committee_id', 'get_members_count', 'deadline')
    filter_horizontal = ('members',)
    
    def get_members_count(self, obj):
        return obj.members.count() if hasattr(obj, 'members') else 0
    get_members_count.short_description = 'Members'


@admin.register(CommitteeVerdict)
class CommitteeVerdictAdmin(admin.ModelAdmin):
    """Admin for Committee Verdicts"""
    list_display = ('verdict_id', 'committee', 'member', 'decision', 'timestamp')
    list_filter = ('decision',)


@admin.register(CoPI)
class CoPIAdmin(admin.ModelAdmin):
    """Admin for Co-Investigators"""
    list_display = ('copi_id', 'name', 'type', 'affiliation')
    list_filter = ('type',)


# Register ResearchGroup again if needed (avoid duplicate)
if ResearchGroupModel not in admin.site._registry:
    admin.site.register(ResearchGroupModel, ResearchGroupAdmin)


# ============================================================================
# UC-006: PROGRESS REPORT ADMIN
# ============================================================================

@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    """Admin for Progress Reports"""
    list_display = ('prid', 'project', 'report_period', 'status', 'submitted_by', 'submitted_date')
    list_filter = ('status', 'report_period', 'project')
    search_fields = ('project__name', 'report_content')
    readonly_fields = ('prid', 'created_date', 'modified_date')
    fieldsets = (
        ('Basic Information', {
            'fields': ('prid', 'project', 'report_period', 'status')
        }),
        ('Content', {
            'fields': ('report_content', 'challenges_faced', 'milestones_achieved',
                      'publications_filed', 'recommendations')
        }),
        ('Documents & Comments', {
            'fields': ('attachments', 'reviewer_comments')
        }),
        ('Submission', {
            'fields': ('submitted_by', 'submitted_date')
        }),
        ('Metadata', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# UC-010: PROJECT CLOSURE ADMIN
# ============================================================================

@admin.register(ProjectClosure)
class ProjectClosureAdmin(admin.ModelAdmin):
    """Admin for Project Closures"""
    list_display = ('closure_id', 'project', 'status', 'closed_by', 'closure_date')
    list_filter = ('status', 'project')
    search_fields = ('project__name', 'final_report')
    readonly_fields = ('closure_id', 'closure_date', 'created_date', 'modified_date')
    fieldsets = (
        ('Basic Information', {
            'fields': ('closure_id', 'project', 'status', 'closed_by')
        }),
        ('Report Content', {
            'fields': ('final_report', 'deliverables_summary', 'challenges_summary',
                      'lessons_learned')
        }),
        ('Outputs', {
            'fields': ('publications_generated', 'patents_filed', 'utilization_percentage')
        }),
        ('Settlement & Outstanding', {
            'fields': ('final_settlement_document', 'outstanding_items')
        }),
        ('Metadata', {
            'fields': ('closure_date', 'created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# BR-018: APPROVAL SLA ADMIN
# ============================================================================

@admin.register(ApprovalSLA)
class ApprovalSLAAdmin(admin.ModelAdmin):
    """Admin for Approval SLAs"""
    list_display = ('sla_id', 'entity_type', 'entity_id', 'deadline', 'status', 'escalation_level')
    list_filter = ('status', 'entity_type', 'escalation_level')
    search_fields = ('entity_id',)
    readonly_fields = ('sla_id', 'created_date', 'modified_date')
    fieldsets = (
        ('Entity Information', {
            'fields': ('sla_id', 'entity_type', 'entity_id')
        }),
        ('Deadline & Status', {
            'fields': ('created_date', 'deadline', 'status')
        }),
        ('Approver & Escalation', {
            'fields': ('current_approver', 'escalation_level', 'escalation_date')
        }),
        ('Notifications', {
            'fields': ('timeout_notified',)
        }),
        ('Metadata', {
            'fields': ('modified_date',),
            'classes': ('collapse',)
        }),
    )
"""
Django Admin Configuration for Staff Management Models
"""

from django.contrib import admin
from .models import Staff, Committee, CommitteeVerdict, CommitteeMember


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Admin interface for Staff model"""
    
    list_display = (
        'sid', 'person', 'pid', 'type', 'approval_status',
        'created_by', 'created_date', 'current_approver'
    )
    list_filter = (
        'approval_status', 'type', 'created_date', 'pid'
    )
    search_fields = (
        'person', 'uname', 'biodata_number', 'sid'
    )
    readonly_fields = (
        'sid', 'approval_chain', 'created_date', 'modified_date'
    )
    
    fieldsets = (
        ('Staff Information', {
            'fields': (
                'sid', 'pid', 'person', 'uname', 'biodata_number',
                'type', 'no_of_positions', 'qualification', 'experience'
            )
        }),
        ('Financial Details', {
            'fields': (
                'salary', 'salary_per_month', 'has_funds'
            )
        }),
        ('Timeline', {
            'fields': (
                'start_date', 'duration', 'submission_date'
            )
        }),
        ('Selection Details', {
            'fields': (
                'interview_date', 'test_date', 'test_mode',
                'interview_place', 'candidates_applied',
                'candidates_called', 'candidates_interviewed',
                'final_selection', 'waiting_list',
                'biodata_final', 'biodata_waiting'
            )
        }),
        ('Approval Workflow', {
            'fields': (
                'approval_status', 'current_approver',
                'approval_chain', 'doc_approval'
            )
        }),
        ('Files', {
            'fields': (
                'ad_file', 'comparative_file', 'joining_report', 'id_card'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by', 'created_date', 'modified_date'
            )
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make approval_chain readonly"""
        if obj:
            return self.readonly_fields + ('approval_status',)
        return self.readonly_fields


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    """Admin interface for Committee model"""
    
    list_display = (
        'committee_id', 'name', 'staff', 'deadline', 'created_at'
    )
    list_filter = (
        'created_at', 'deadline'
    )
    search_fields = (
        'name', 'committee_id', 'staff__sid'
    )
    filter_horizontal = ('members',)
    readonly_fields = (
        'committee_id', 'created_at'
    )
    
    fieldsets = (
        ('Committee Information', {
            'fields': (
                'committee_id', 'name', 'staff'
            )
        }),
        ('Members', {
            'fields': ('members',),
            'description': 'Select PI-eligible faculty members (Min 3)'
        }),
        ('Timeline', {
            'fields': ('deadline', 'created_at')
        }),
    )


@admin.register(CommitteeVerdict)
class CommitteeVerdictAdmin(admin.ModelAdmin):
    """Admin interface for CommitteeVerdict model"""
    
    list_display = (
        'verdict_id', 'committee', 'member', 'decision',
        'has_conflict_of_interest', 'submitted_date'
    )
    list_filter = (
        'decision', 'has_conflict_of_interest', 'submitted_date', 'committee'
    )
    search_fields = (
        'verdict_id', 'member__user__username', 'committee__name'
    )
    readonly_fields = (
        'verdict_id', 'submitted_date', 'timestamp'
    )
    
    fieldsets = (
        ('Verdict Information', {
            'fields': (
                'verdict_id', 'committee', 'member'
            )
        }),
        ('Decision', {
            'fields': (
                'decision', 'comments'
            )
        }),
        ('Conflict of Interest (BR-RSPC-15)', {
            'fields': (
                'has_conflict_of_interest', 'conflict_reason'
            )
        }),
        ('Timeline', {
            'fields': (
                'submitted_date', 'timestamp'
            )
        }),
    )


@admin.register(CommitteeMember)
class CommitteeMemberAdmin(admin.ModelAdmin):
    """Admin interface for CommitteeMember model"""
    
    list_display = (
        'id', 'committee', 'member', 'is_pi_eligible',
        'appointed_date', 'designation'
    )
    list_filter = (
        'is_pi_eligible', 'appointed_date', 'committee'
    )
    search_fields = (
        'member__user__username', 'committee__name'
    )
    readonly_fields = (
        'appointed_date',
    )
    
    fieldsets = (
        ('Member Information', {
            'fields': (
                'id', 'committee', 'member'
            )
        }),
        ('PI Eligibility (BR-RSPC-12)', {
            'fields': (
                'is_pi_eligible', 'designation', 'department'
            )
        }),
        ('Timeline', {
            'fields': ('appointed_date',)
        }),
    )

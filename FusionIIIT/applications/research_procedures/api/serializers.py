"""
RSPC Module - DRF Serializers
Field-level validation and data transformation
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
import os

from ..models import (
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
    
    # Core Tables
    Project, Budget, Staff, StaffPosition,
    ProjectAccess, FinancialOutlay, StaffAllocation,
    Request, RSPCInventory, Tracking, File,
    Committee, CommitteeVerdict, CoPI,
    Expenditure, ExpenditureApprovalHistory, Notification, ScheduledReport,
    BudgetReallocation, BudgetModificationHistory,
    ExpenditureHead,
    
    # UC-004, UC-005, UC-012
    ProjectVersion, CancellationRequest, ProposalVetting,
    
    # UC-021, UC-022, UC-023, BR-020
    SmallFundRequest, FundDisbursement, ConsultancyLimit,
    
    # Notifications
    NotificationEventType, NotificationEntityType
)


# ============================================================================
# RESEARCH AREA SERIALIZERS
# ============================================================================

class ResearchGroupListSerializer(serializers.ModelSerializer):
    """Serializer for Research Group list view"""
    head_name = serializers.CharField(source='head.user.get_full_name', read_only=True, allow_null=True)
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ResearchGroup
        fields = ('id', 'name', 'acronym', 'discipline_name', 'head_name', 'member_count', 
                  'is_active', 'established_date', 'created_date', 'modified_date')
    
    def get_member_count(self, obj):
        return obj.members.count()


class ResearchGroupSerializer(serializers.ModelSerializer):
    """Full Serializer for Research Group with related data"""
    head_name = serializers.CharField(source='head.user.get_full_name', read_only=True, allow_null=True)
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    members_list = serializers.SerializerMethodField()
    
    class Meta:
        model = ResearchGroup
        fields = ('id', 'name', 'acronym', 'description', 'discipline', 'discipline_name',
                  'head', 'head_name', 'members', 'members_list', 'established_date', 
                  'website', 'is_active', 'created_date', 'modified_date')
        read_only_fields = ('created_date', 'modified_date')
    
    def get_members_list(self, obj):
        return [{'id': m.id, 'name': m.user.get_full_name()} for m in obj.members.all()]
    
    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Group name cannot be empty")
        return value.strip()


class ResearchAreaListSerializer(serializers.ModelSerializer):
    """Serializer for Research Area list view"""
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    parent_area_name = serializers.CharField(source='parent_area.name', read_only=True, allow_null=True)
    expert_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ResearchArea
        fields = ('id', 'name', 'discipline_name', 'parent_area_name', 'expert_count',
                  'is_active', 'created_date', 'modified_date')
    
    def get_expert_count(self, obj):
        return obj.faculty_experts.count()


class ResearchAreaSerializer(serializers.ModelSerializer):
    """Full Serializer for Research Area with hierarchy"""
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    parent_area_name = serializers.CharField(source='parent_area.name', read_only=True, allow_null=True)
    sub_areas = ResearchAreaListSerializer(many=True, read_only=True)
    faculty_experts_list = serializers.SerializerMethodField()
    
    class Meta:
        model = ResearchArea
        fields = ('id', 'name', 'description', 'discipline', 'discipline_name',
                  'parent_area', 'parent_area_name', 'sub_areas', 'faculty_experts',
                  'faculty_experts_list', 'is_active', 'created_date', 'modified_date')
        read_only_fields = ('created_date', 'modified_date', 'sub_areas')
    
    def get_faculty_experts_list(self, obj):
        return [{'id': f.id, 'name': f.user.get_full_name()} for f in obj.faculty_experts.all()]
    
    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Research area name cannot be empty")
        return value.strip()


# ============================================================================
# FUNDING AGENCY SERIALIZERS
# ============================================================================

class FundingAgencySerializer(serializers.ModelSerializer):
    """Serializer for Funding Agency"""
    
    class Meta:
        model = FundingAgency
        fields = '__all__'


# ============================================================================
# PROJECT SERIALIZERS
# ============================================================================

class ProjectSerializer(serializers.ModelSerializer):
    """Full Project serializer"""
    
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('pid', 'created_at', 'updated_at')


class ProjectCreateSerializer(serializers.Serializer):
    """
    UC-001: Submit Research Proposal - Serializer with comprehensive validations
    Enforces: BR-RSPC-03, BR-RSPC-05, BR-RSPC-06, BR-RSPC-11, BR-RSPC-21
    """
    name = serializers.CharField(max_length=200)
    pi_id = serializers.CharField(max_length=100)
    pi_name = serializers.CharField(max_length=200, required=False)
    access = serializers.ChoiceField(choices=['Co', 'noCo'], default='noCo')
    type = serializers.CharField(max_length=50, default='Research')
    dept = serializers.CharField(max_length=100, required=False)
    category = serializers.CharField(max_length=50, required=False)
    sponsored_agency = serializers.CharField(max_length=200, required=False)
    scheme = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.IntegerField(min_value=6, max_value=60, default=12)
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    co_pis = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    file = serializers.FileField(required=False)
    
    # Budget fields - year-wise allocation for each category
    budget = serializers.DictField(required=False, default=dict)
    
    def validate_name(self, value):
        """BR-RSPC-05: Unique project name validation"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Project name must be at least 3 characters long")
        if Project.objects.filter(name=value).exists():
            raise serializers.ValidationError("Project name must be unique")
        return value
    
    def validate_duration(self, value):
        """BR-RSPC-11: Project duration must be 6-60 months (0.5-5 years)"""
        if not (6 <= value <= 60):
            raise serializers.ValidationError("Duration must be between 6 and 60 months (0.5-5 years)")
        return value
    
    def validate_pi_id(self, value):
        """BR-RSPC-03 & BR-RSPC-02: PI must be eligible (permanent active faculty with department alignment)"""
        from .. import services
        is_eligible, reason = services.validate_pi_eligibility(value)
        if not is_eligible:
            raise serializers.ValidationError(f"PI not eligible: {reason}")
        return value
    
    def validate_total_budget(self, value):
        """Budget must be non-negative"""
        if value < 0:
            raise serializers.ValidationError("Budget cannot be negative")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        pi_id = data.get('pi_id')
        co_pis = data.get('co_pis', [])
        
        # BR-RSPC-06: PI and Co-PI must be distinct
        if pi_id and pi_id in co_pis:
            raise serializers.ValidationError("PI cannot also be a Co-PI")
        
        # BR-RSPC-21: No duplicate Co-PIs
        if co_pis and len(co_pis) != len(set(co_pis)):
            raise serializers.ValidationError("Duplicate Co-PIs not allowed")
        
        # Validate all Co-PIs are eligible (same criteria as PI)
        if co_pis:
            from .. import services
            for copi in co_pis:
                is_eligible, reason = services.validate_pi_eligibility(copi)
                if not is_eligible:
                    raise serializers.ValidationError(f"Co-PI '{copi}' not eligible: {reason}")
        
        return data


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project lists with role-based filtering info"""
    co_pi_count = serializers.SerializerMethodField()
    budget_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ('pid', 'name', 'pi_name', 'status', 'type', 
                  'dept', 'total_budget', 'sanctioned_amount', 
                  'submission_date', 'start_date', 'end_date',
                  'co_pi_count', 'budget_status', 'duration')
        read_only_fields = fields
    
    def get_co_pi_count(self, obj):
        """Count associated Co-PIs for display"""
        return ProjectAccess.objects.filter(pid=obj).count()
    
    def get_budget_status(self, obj):
        """Return budget utilization status"""
        try:
            budget = Budget.objects.get(project=obj)
            if budget.total_sanctioned > 0:
                utilization = (budget.current_funds / budget.total_sanctioned) * 100
                return {
                    'allocated': float(budget.total_sanctioned),
                    'used': float(budget.current_funds),
                    'utilization_percent': round(utilization, 2)
                }
        except Budget.DoesNotExist:
            pass
        return {'allocated': 0, 'used': 0, 'utilization_percent': 0}


class ConsultancyProposalSerializer(serializers.Serializer):
    """
    UC-002: Submit Consultancy Proposal
    Similar to research proposal but with consultancy-specific fields
    """
    name = serializers.CharField(max_length=200)
    pi_id = serializers.CharField(max_length=100)
    pi_name = serializers.CharField(max_length=200, required=False)
    client_name = serializers.CharField(max_length=200)
    client_org = serializers.CharField(max_length=200, required=False)
    client_contact = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.IntegerField(min_value=1, max_value=60, default=12)
    contract_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    contract_file = serializers.FileField(required=False)
    co_investigators = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    
    def validate_name(self, value):
        """Unique project name validation"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Project name must be at least 3 characters long")
        if Project.objects.filter(name=value).exists():
            raise serializers.ValidationError("Project name must be unique")
        return value
    
    def validate_pi_id(self, value):
        """PI eligibility validation for consultancy"""
        from .. import services
        is_eligible, reason = services.validate_pi_eligibility(value)
        if not is_eligible:
            raise serializers.ValidationError(f"PI not eligible: {reason}")
        return value
    
    def validate_duration(self, value):
        """Duration must be positive"""
        if value < 1 or value > 60:
            raise serializers.ValidationError("Consultancy duration must be 1-60 months")
        return value
    
    def validate_contract_amount(self, value):
        """Contract amount must be positive"""
        if value <= 0:
            raise serializers.ValidationError("Contract amount must be positive")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        pi_id = data.get('pi_id')
        co_investigators = data.get('co_investigators', [])
        
        # PI and Co-investigator distinction
        if pi_id and pi_id in co_investigators:
            raise serializers.ValidationError("PI cannot also be a Co-investigator")
        
        # No duplicate Co-investigators
        if co_investigators and len(co_investigators) != len(set(co_investigators)):
            raise serializers.ValidationError("Duplicate Co-investigators not allowed")
        
        return data


class ProjectDraftSerializer(serializers.Serializer):
    """
    UC-004: Save Proposal as Draft
    Allows partial submission and auto-save functionality
    """
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    type = serializers.CharField(max_length=50, required=False)
    category = serializers.CharField(max_length=50, required=False)
    sponsored_agency = serializers.CharField(max_length=200, required=False)
    scheme = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.IntegerField(min_value=6, max_value=60, required=False)
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    co_pis = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    file = serializers.FileField(required=False)
    budget = serializers.DictField(required=False, default=dict)
    
    def validate_duration(self, value):
        """If provided, duration must be valid"""
        if value is not None and not (6 <= value <= 60):
            raise serializers.ValidationError("Duration must be between 6 and 60 months")
        return value
    
    def validate_total_budget(self, value):
        """If provided, budget must be non-negative"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Budget cannot be negative")
        return value


class ProjectResubmitSerializer(serializers.Serializer):
    """
    UC-005: Edit & Resubmit Proposal
    Allows PI to modify draft or rejected proposal and resubmit
    Enforces same business rules as new proposal submission
    """
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.IntegerField(min_value=6, max_value=60, required=False)
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    co_pis = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    file = serializers.FileField(required=False)
    budget = serializers.DictField(required=False, default=dict)
    resubmission_comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate_name(self, value):
        """If updating name, must remain unique"""
        if value and Project.objects.filter(name=value).exclude(pid=self.context.get('project_id')).exists():
            raise serializers.ValidationError("Project name must be unique")
        return value
    
    def validate_duration(self, value):
        """If updating duration, must be valid"""
        if value is not None and not (6 <= value <= 60):
            raise serializers.ValidationError("Duration must be between 6 and 60 months")
        return value


# ============================================================================
# BUDGET SERIALIZERS (UC-011: Budget Reallocation)
# ============================================================================

class BudgetDetailSerializer(serializers.ModelSerializer):
    """
    UC-011: Comprehensive Budget serializer with utilization details
    Used for GET /rspc/api/budget/{project_id}/
    """
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_pi = serializers.CharField(source='project.pi_name', read_only=True)
    total_budget = serializers.SerializerMethodField()
    utilization_percentage = serializers.SerializerMethodField()
    available_balance = serializers.SerializerMethodField()
    categories_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Budget
        fields = (
            'bid', 'project', 'project_name', 'project_pi',
            'manpower', 'travel', 'consumables', 'equipment', 
            'contingency', 'overhead',
            'total_sanctioned', 'current_funds',
            'total_budget', 'utilized_amounts',
            'utilization_percentage', 'available_balance',
            'categories_summary', 'last_modified', 'created_at'
        )
        read_only_fields = ('bid', 'created_at', 'last_modified')
    
    def get_total_budget(self, obj):
        """Get total budget calculated from all categories"""
        return float(obj.get_total_budget())
    
    def get_utilization_percentage(self, obj):
        """Get budget utilization as percentage"""
        return round(obj.get_utilization_percentage(), 2)
    
    def get_available_balance(self, obj):
        """Get available balance (total - utilized)"""
        return float(obj.total_sanctioned - obj.current_funds)
    
    def get_categories_summary(self, obj):
        """Get summary for each category"""
        summary = {}
        categories = ['manpower', 'travel', 'consumables', 'equipment', 'contingency']
        for cat in categories:
            cat_budget = getattr(obj, cat, {})
            if isinstance(cat_budget, dict):
                total_cat = sum(float(v) for v in cat_budget.values() if isinstance(v, (int, float)))
            else:
                total_cat = 0
            
            cat_util = obj.get_category_utilization(cat)
            summary[cat] = {
                'allocated': total_cat,
                'utilized': float(cat_util),
                'available': total_cat - float(cat_util),
                'utilization_pct': (float(cat_util) / total_cat * 100) if total_cat > 0 else 0
            }
        return summary


class BudgetReallocationRequestSerializer(serializers.Serializer):
    """
    UC-011: Budget Reallocation Request Serializer
    Used for POST /rspc/api/budget/{project_id}/reallocate/
    
    Enforces BR-RSPC-08: Max 20% reallocation per category per year
    """
    from_category = serializers.ChoiceField(choices=ExpenditureHead.choices)
    to_category = serializers.ChoiceField(choices=ExpenditureHead.choices)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    financial_year = serializers.CharField(max_length=10, help_text="e.g., 2023-24")
    justification = serializers.CharField(required=True, min_length=10)
    
    def validate_amount(self, value):
        """Amount must be positive"""
        if value <= 0:
            raise serializers.ValidationError("Reallocation amount must be positive")
        return value
    
    def validate(self, data):
        """Cross-field validations"""
        if data['from_category'] == data['to_category']:
            raise serializers.ValidationError(
                "Source and target categories must be different"
            )
        if len(data['justification'].strip()) < 10:
            raise serializers.ValidationError(
                "Justification must be at least 10 characters long"
            )
        return data


class BudgetReallocationSerializer(serializers.ModelSerializer):
    """
    Serializer for BudgetReallocation model - for display and history
    """
    budget_project_name = serializers.CharField(
        source='budget.project.name', 
        read_only=True
    )
    exceeds_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = BudgetReallocation
        fields = (
            'rbid', 'budget', 'budget_project_name',
            'from_category', 'to_category', 'amount',
            'financial_year', 'justification',
            'requires_approval', 'approval_status', 'exceeds_limit',
            'approved_by', 'approval_comments',
            'requested_by', 'requested_at', 'approved_at', 'implemented_at'
        )
        read_only_fields = (
            'rbid', 'requires_approval', 'approval_status',
            'requested_at', 'approved_at', 'implemented_at'
        )
    
    def get_exceeds_limit(self, obj):
        """Check if reallocation exceeds 20% limit (BR-RSPC-08)"""
        return obj.requires_approval


class BudgetModificationHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for BudgetModificationHistory model
    Used for GET /rspc/api/budget/{project_id}/history/
    """
    budget_project = serializers.CharField(
        source='budget.project.name',
        read_only=True
    )
    
    class Meta:
        model = BudgetModificationHistory
        fields = (
            'hmid', 'budget', 'budget_project',
            'modification_type', 'category',
            'old_value', 'new_value', 'change_amount',
            'reason', 'modified_by', 'modified_at',
            'related_reallocation'
        )
        read_only_fields = fields


class BudgetUtilizationUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating utilized amounts (Admin only)
    Used for POST /rspc/api/budget/{project_id}/update-utilized/
    
    BR-RSPC-11: Only RSPC Admin can update utilized amounts
    """
    category = serializers.ChoiceField(choices=ExpenditureHead.choices)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    reason = serializers.CharField(min_length=5)
    financial_year = serializers.CharField(max_length=10, required=False)
    
    def validate_reason(self, value):
        """Reason must be meaningful"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Reason must be at least 5 characters long"
            )
        return value


# ============================================================================
# STAFF SERIALIZERS
# ============================================================================

class StaffSerializer(serializers.ModelSerializer):
    """Serializer for Staff"""
    
    class Meta:
        model = Staff
        fields = '__all__'


class StaffRequestSerializer(serializers.Serializer):
    """Serializer for staff request"""
    project_id = serializers.IntegerField()
    person = serializers.CharField(max_length=200, required=False)
    biodata_number = serializers.CharField(max_length=50, required=False)
    start_date = serializers.DateTimeField(required=False)
    duration = serializers.IntegerField(min_value=1, default=12)
    eligibility = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=['RA', 'SRF', 'JRF', 'PROJECT_ASSISTANT', 'PROJECT_SCIENTIST', 'OTHER'])
    salary = serializers.DecimalField(max_digits=10, decimal_places=2)
    has_funds = serializers.BooleanField(default=False)
    post_on_website = serializers.BooleanField(default=False)


class SelectionCommitteeSerializer(serializers.Serializer):
    """Serializer for creating selection committee"""
    staff_id = serializers.IntegerField()
    committee_members = serializers.ListField(child=serializers.CharField())
    deadline = serializers.DateTimeField(required=False)
    ad_file = serializers.FileField(required=False)
    
    def validate_committee_members(self, value):
        """BR-RSPC-12: Committee must have at least 3 members"""
        if len(value) < 3:
            raise serializers.ValidationError("Committee must have at least 3 members")
        return value


class StaffSelectionReportSerializer(serializers.Serializer):
    """Serializer for staff selection report"""
    staff_id = serializers.IntegerField()
    final_selection = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    waiting_list = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    biodata_final = serializers.ListField(child=serializers.FileField(), required=False, default=list)
    biodata_waiting = serializers.ListField(child=serializers.FileField(), required=False, default=list)
    comparative_file = serializers.FileField(required=False)


class CommitteeActionSerializer(serializers.Serializer):
    """Serializer for committee member action"""
    recommendation = serializers.ChoiceField(choices=['Approve', 'Reject'])
    conflict_declaration = serializers.BooleanField(default=False)
    comments = serializers.CharField(required=False, allow_blank=True)


class StaffDecisionSerializer(serializers.Serializer):
    """Serializer for staff appointment decision"""
    action = serializers.ChoiceField(choices=['Approve', 'Reject'])
    remarks = serializers.CharField(required=False, allow_blank=True)
    qualification = serializers.CharField(required=False, allow_blank=True)


class StaffDocumentSerializer(serializers.Serializer):
    """Serializer for staff joining documents"""
    joining_report = serializers.FileField()
    salary_per_month = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    id_card = serializers.FileField(required=False)


class StaffPositionSerializer(serializers.ModelSerializer):
    """Serializer for staff positions"""
    
    class Meta:
        model = StaffPosition
        fields = '__all__'


# ============================================================================
# FINANCIAL OUTLAY SERIALIZERS
# ============================================================================

class FinancialOutlaySerializer(serializers.ModelSerializer):
    """Serializer for Financial Outlay"""
    
    class Meta:
        model = FinancialOutlay
        fields = '__all__'


# ============================================================================
# REQUEST SERIALIZERS
# ============================================================================

class FundRequestCreateSerializer(serializers.Serializer):
    """Serializer for fund request"""
    project_id = serializers.IntegerField()
    description = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class FundApprovalSerializer(serializers.Serializer):
    """Serializer for fund approval"""
    remarks = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# EXPENDITURE SERIALIZERS
# ============================================================================

class ExpenditureCreateSerializer(serializers.Serializer):
    """Serializer for creating expenditure"""
    project_id = serializers.IntegerField()
    category = serializers.CharField()
    amount = serializers.FloatField(min_value=0)
    purpose = serializers.CharField()
    supporting_documents = serializers.ListField(
        child=serializers.FileField(), required=False, default=list
    )


class ExpenditureListSerializer(serializers.Serializer):
    """Serializer for expenditure list"""
    eid = serializers.IntegerField()
    project_id = serializers.IntegerField()
    project_name = serializers.CharField(source='project.name')
    category = serializers.CharField()
    amount = serializers.FloatField()
    status = serializers.CharField()
    requested_by = serializers.CharField()
    requested_at = serializers.DateTimeField()


class ExpenditureDetailSerializer(serializers.Serializer):
    """Serializer for detailed expenditure information"""
    eid = serializers.IntegerField()
    project = serializers.DictField()
    category = serializers.CharField()
    amount = serializers.FloatField()
    purpose = serializers.CharField()
    status = serializers.CharField()
    requested_by = serializers.CharField()
    requested_at = serializers.DateTimeField()
    current_approver = serializers.CharField(allow_null=True)
    supporting_documents = serializers.ListField()


class ExpenditureApprovalSerializer(serializers.Serializer):
    """Serializer for expenditure approval"""
    remarks = serializers.CharField(required=False, allow_blank=True)
    approved_amount = serializers.FloatField(required=False)


class ExpenditureRejectionSerializer(serializers.Serializer):
    """Serializer for expenditure rejection"""
    reason = serializers.CharField()


class ExpenditureTrackSerializer(serializers.Serializer):
    """Serializer for expenditure tracking"""
    eid = serializers.IntegerField()
    status = serializers.CharField()
    current_approver = serializers.CharField(allow_null=True)
    requested_at = serializers.DateTimeField()
    timeline = serializers.ListField()
    escalation_status = serializers.CharField()


class ExpenditureHistorySerializer(serializers.Serializer):
    """Serializer for expenditure history"""
    timestamp = serializers.DateTimeField()
    action = serializers.CharField()
    actor = serializers.CharField()
    remarks = serializers.CharField(allow_null=True)
    previous_status = serializers.CharField()
    new_status = serializers.CharField()


# ============================================================================
# PROGRESS REPORT SERIALIZERS
# ============================================================================

class ProgressReportSerializer(serializers.Serializer):
    """Serializer for progress report submission"""
    project_id = serializers.IntegerField()
    report_type = serializers.ChoiceField(choices=['QUARTERLY', 'HALF_YEARLY', 'ANNUAL', 'FINAL', 'UTILIZATION'])
    period_from = serializers.DateField()
    period_to = serializers.DateField()
    summary = serializers.CharField()
    report_file = serializers.FileField(required=False)


# ============================================================================
# REPORT GENERATION SERIALIZERS
# ============================================================================

class ReportGenerationSerializer(serializers.Serializer):
    """Serializer for report generation"""
    report_type = serializers.CharField()
    project_id = serializers.IntegerField(required=False)
    department = serializers.CharField(required=False)
    date_range = serializers.DictField(required=False, default=dict)
    format = serializers.ChoiceField(choices=['PDF', 'Excel', 'CSV'], default='PDF')


class ReportScheduleSerializer(serializers.Serializer):
    """Serializer for scheduling reports"""
    report_type = serializers.CharField()
    frequency = serializers.ChoiceField(choices=['Daily', 'Weekly', 'Monthly', 'Quarterly'])
    recipients = serializers.ListField(child=serializers.EmailField())
    next_run = serializers.DateTimeField(required=False)
    parameters = serializers.DictField(required=False, default=dict)


class ScheduledReportSerializer(serializers.ModelSerializer):
    """Serializer for scheduled report details"""
    
    class Meta:
        model = ScheduledReport
        fields = ('sid', 'report_type', 'frequency', 'recipients', 'next_run')


# ============================================================================
# APPROVAL SERIALIZERS
# ============================================================================

class ProposalVerificationSerializer(serializers.Serializer):
    """Serializer for proposal verification"""
    action = serializers.ChoiceField(choices=['Verify', 'Return'])
    remarks = serializers.CharField(required=False, allow_blank=True)


class ApprovalActionSerializer(serializers.Serializer):
    """Serializer for approval/rejection actions"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    remarks = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# COMMITTEE SERIALIZERS
# ============================================================================

class CommitteeDeadlineSerializer(serializers.Serializer):
    """Serializer for extending committee deadline"""
    new_deadline = serializers.DateTimeField()
    reason = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# NOTIFICATION SERIALIZERS
# ============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    class Meta:
        model = Notification
        fields = ('nid', 'subject', 'message', 'entity_type', 
                  'entity_id', 'is_read', 'created_at')


# ============================================================================
# UTILITY SERIALIZERS
# ============================================================================

class CoPISerializer(serializers.ModelSerializer):
    """Serializer for Co-PI list"""
    
    class Meta:
        model = ProjectAccess
        fields = ('aid', 'pid', 'copi_id', 'type', 'affiliation', 'name')


class FacultyIDSerializer(serializers.Serializer):
    """Serializer for faculty ID dropdown"""
    id = serializers.CharField()
    username = serializers.CharField()
    name = serializers.CharField()
    department = serializers.CharField(allow_null=True)


class ProjectIDSerializer(serializers.Serializer):
    """Serializer for project ID dropdown"""
    pid = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()


# ============================================================================
# ENHANCED EXPENDITURE SERIALIZERS (Phase 2)
# ============================================================================

class ExpenditureCreateSerializer(serializers.Serializer):
    """Serializer for creating expenditure requests with BR-RSPC-13 workflow"""
    project_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[
        'MANPOWER', 'EQUIPMENT', 'CONSUMABLES', 'TRAVEL', 
        'CONTINGENCY', 'OVERHEAD', 'OTHER'
    ])
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    purpose = serializers.CharField()
    supporting_documents = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        default=list
    )
    
    def validate_amount(self, value):
        """Amount must be positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value
    
    def validate_purpose(self, value):
        """Purpose must be descriptive"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Purpose must be at least 10 characters")
        return value


class ExpenditureApprovalSerializer(serializers.Serializer):
    """Serializer for expenditure approval"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['action'] == 'reject' and not data.get('comments'):
            raise serializers.ValidationError("Rejection must include comments")
        return data


class ExpenditureListSerializer(serializers.Serializer):
    """Lightweight serializer for expenditure lists"""
    id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    category = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    purpose = serializers.CharField()
    status = serializers.CharField()
    current_approver = serializers.CharField()
    request_date = serializers.DateTimeField()


class BudgetReallocateSerializer(serializers.Serializer):
    """Serializer for budget reallocation with BR-RSPC-08 validation"""
    from_category = serializers.ChoiceField(choices=[
        'manpower', 'travel', 'contingency', 'consumables', 'equipments', 'overhead'
    ])
    to_category = serializers.ChoiceField(choices=[
        'manpower', 'travel', 'contingency', 'consumables', 'equipments', 'overhead'
    ])
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    justification = serializers.CharField()
    
    def validate(self, data):
        """Cross-field validation"""
        if data['from_category'] == data['to_category']:
            raise serializers.ValidationError("Cannot reallocate from and to the same category")
        
        if data['amount'] <= 0:
            raise serializers.ValidationError("Reallocation amount must be positive")
        
        if len(data.get('justification', '').strip()) < 10:
            raise serializers.ValidationError("Justification must be at least 10 characters")
        
        return data


# ============================================================================
# ENHANCED STAFF & COMMITTEE SERIALIZERS (Phase 2)
# ============================================================================

class StaffCommitteeCreateSerializer(serializers.Serializer):
    """Serializer for creating staff selection committee with BR-RSPC-12"""
    staff_id = serializers.IntegerField()
    committee_members = serializers.ListField(child=serializers.CharField())
    deadline = serializers.DateTimeField(required=False)
    ad_file = serializers.FileField(required=False)
    
    def validate_committee_members(self, value):
        """Validate committee has minimum 3 members"""
        if len(value) < 3:
            raise serializers.ValidationError("Committee must have at least 3 members")
        
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate committee members not allowed")
        
        return value


class CommitteeVerdictSerializer(serializers.Serializer):
    """Serializer for submitting committee verdict"""
    staff_id = serializers.IntegerField()
    recommendation = serializers.ChoiceField(choices=['APPROVE', 'REJECT', 'ABSTAIN'])
    comments = serializers.CharField(required=False, allow_blank=True)
    conflict_declared = serializers.BooleanField(default=False)


class StaffRequestSerializer(serializers.Serializer):
    """Serializer for staff appointment requests"""
    project_id = serializers.IntegerField()
    person = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=[
        'RA', 'SRF', 'JRF', 'PROJECT_ASSISTANT', 'PROJECT_SCIENTIST', 'OTHER'
    ])
    start_date = serializers.DateField()
    duration = serializers.IntegerField(min_value=1)
    eligibility = serializers.CharField(required=False)
    salary = serializers.DecimalField(max_digits=15, decimal_places=2)
    has_funds = serializers.BooleanField(default=False)
    post_on_website = serializers.BooleanField(default=False)


# ============================================================================
# PI VALIDATION SERIALIZERS (Phase 1)
# ============================================================================

class PIValidationSerializer(serializers.Serializer):
    """Serializer for PI eligibility validation"""
    username = serializers.CharField()


class PIEligibilityResponseSerializer(serializers.Serializer):
    """Response serializer for PI eligibility check"""
    username = serializers.CharField()
    name = serializers.CharField()
    is_eligible = serializers.BooleanField()
    reason = serializers.CharField()
    user_type = serializers.CharField()
    is_permanent = serializers.BooleanField()
    is_active = serializers.BooleanField()
    department = serializers.CharField(allow_null=True)
    designations = serializers.ListField(child=serializers.CharField())


class DurationValidationSerializer(serializers.Serializer):
    """Serializer for duration validation"""
    duration = serializers.IntegerField()
    
    def validate_duration(self, value):
        """Validate 6-60 month range"""
        if value < 6 or value > 60:
            raise serializers.ValidationError("Duration must be between 6 and 60 months")
        return value


class CommitteeSizeValidationSerializer(serializers.Serializer):
    """Serializer for committee size validation"""
    members = serializers.ListField(child=serializers.CharField())
    
    def validate_members(self, value):
        """Validate minimum 3 members"""
        if len(value) < 3:
            raise serializers.ValidationError("Committee must have at least 3 members")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate members not allowed")
        return value


class BudgetReallocationLimitSerializer(serializers.Serializer):
    """Serializer for budget reallocation limit validation"""
    project_id = serializers.IntegerField()
    from_category = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    to_category = serializers.CharField(required=False)


# ============================================================================
# DASHBOARD SERIALIZERS
# ============================================================================

class DashboardSerializer(serializers.Serializer):
    """Serializer for dashboard data"""
    user = serializers.DictField()
    projects = serializers.DictField()
    staff = serializers.DictField()
    notifications = serializers.IntegerField()
    recent_activity = serializers.ListField()


class PendingApprovalsSerializer(serializers.Serializer):
    """Serializer for pending approvals dashboard"""
    pi_pending = serializers.ListField()
    hod_pending = serializers.ListField()
    rspc_pending = serializers.ListField()
    total = serializers.IntegerField()


class ProjectLifecycleSerializer(serializers.Serializer):
    """Serializer for project lifecycle information"""
    project_id = serializers.IntegerField()
    name = serializers.CharField()
    current_status = serializers.CharField()
    created_at = serializers.DateTimeField(allow_null=True)
    submission_date = serializers.DateTimeField(allow_null=True)
    sanction_date = serializers.DateTimeField(allow_null=True)
    start_date = serializers.DateTimeField(allow_null=True)
    end_date = serializers.DateTimeField(allow_null=True)
    total_budget = serializers.FloatField()
    sanctioned_amount = serializers.FloatField()
    initial_amount = serializers.FloatField()
    pi = serializers.CharField()
    department = serializers.CharField()
    type = serializers.CharField()
    duration_months = serializers.IntegerField()


# ============================================================================
# COMPLETE NOTIFICATION SERIALIZERS (UC-015)
# ============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model (UC-015)
    Used for GET endpoints
    """
    sender_username = serializers.CharField(source='sender.username', read_only=True, allow_null=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    entity_type_display = serializers.CharField(source='get_entity_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = (
            'nid', 'sender', 'sender_username', 'recipient', 'recipient_username',
            'event_type', 'event_type_display',
            'entity_type', 'entity_type_display', 'entity_id',
            'title', 'message',
            'is_read', 'context_data',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'nid', 'sender', 'recipient',
            'event_type', 'entity_type', 'entity_id',
            'title', 'message', 'context_data',
            'created_at', 'updated_at'
        )


class NotificationMarkReadSerializer(serializers.Serializer):
    """
    Serializer for marking notification as read
    Used for POST /rspc/api/notifications/{id}/mark-read/
    """
    is_read = serializers.BooleanField(default=True)


class NotificationFilterSerializer(serializers.Serializer):
    """
    Serializer for filtering notifications
    Used for GET /rspc/api/notifications/ with query params
    """
    read_status = serializers.ChoiceField(
        choices=['all', 'read', 'unread'],
        default='all',
        required=False
    )
    event_type = serializers.ChoiceField(
        choices=[choice[0] for choice in NotificationEventType.choices],
        required=False,
        allow_blank=True
    )
    entity_type = serializers.ChoiceField(
        choices=[choice[0] for choice in NotificationEntityType.choices],
        required=False,
        allow_blank=True
    )
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    offset = serializers.IntegerField(min_value=0, default=0)


class UnreadCountResponseSerializer(serializers.Serializer):
    """
    Response serializer for unread notifications count
    Used for GET /rspc/api/notifications/unread-count/
    """
    unread_count = serializers.IntegerField(min_value=0)
    total_notifications = serializers.IntegerField(min_value=0)


# ============================================================================
# UC-004: PROJECT VERSION & UPDATE SERIALIZERS
# ============================================================================

class ProjectVersionSerializer(serializers.Serializer):
    """Serializer for project versions (UC-004)"""
    version_number = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    changed_by = serializers.CharField()
    changed_date = serializers.DateTimeField()
    change_reason = serializers.CharField()
    change_type = serializers.CharField()


class ProjectUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating project (UC-004)
    Allows partial updates to title, description, budget, allow_updates_after_approval
    """
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    allow_updates_after_approval = serializers.BooleanField(required=False)
    change_reason = serializers.CharField(max_length=200)
    change_type = serializers.ChoiceField(choices=[
        ('TITLE', 'Title'),
        ('BUDGET', 'Budget'),
        ('DESCRIPTION', 'Description'),
        ('MEMBERS', 'Members'),
        ('OTHER', 'Other')
    ])
    
    def validate(self, data):
        """At least one field must be updated"""
        update_fields = [k for k in ['name', 'description', 'total_budget', 'allow_updates_after_approval'] if k in data]
        if not update_fields:
            raise serializers.ValidationError("At least one field must be updated")
        return data


class ProjectVersionDetailSerializer(serializers.Serializer):
    """Detailed serializer for specific project version"""
    version_number = serializers.IntegerField()
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    changed_by = serializers.CharField()
    changed_date = serializers.DateTimeField()
    change_reason = serializers.CharField()
    change_type = serializers.CharField()


# ============================================================================
# UC-005: PROJECT CANCELLATION SERIALIZERS
# ============================================================================

class ProjectCancellationSerializer(serializers.Serializer):
    """Serializer for project cancellation (UC-005)"""
    cancellation_reason = serializers.CharField(required=True, min_length=10)


class CancellationRequestSerializer(serializers.Serializer):
    """Serializer for formal cancellation request (UC-005 workflow)"""
    reason = serializers.CharField(required=True, min_length=10)


class CancellationRequestApprovalSerializer(serializers.Serializer):
    """Serializer for RSPC Admin to approve cancellation request"""
    approval_comments = serializers.CharField(required=False, allow_blank=True)


class CancellationDetailsSerializer(serializers.Serializer):
    """Response serializer for cancellation details"""
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    status = serializers.CharField()
    cancellation_reason = serializers.CharField()
    cancelled_by = serializers.CharField()
    cancelled_date = serializers.DateTimeField()


# ============================================================================
# UC-012: PROPOSAL VETTING SERIALIZERS
# ============================================================================

class ProposalVettingSerializer(serializers.Serializer):
    """
    Serializer for HOD to vet proposal (UC-012)
    
    Each criterion evaluated as: PASS, FAIL, FLAG
    """
    technical_feasibility = serializers.ChoiceField(choices=[('PASS', 'Pass'), ('FAIL', 'Fail'), ('FLAG', 'Flag')])
    academic_relevance = serializers.ChoiceField(choices=[('PASS', 'Pass'), ('FAIL', 'Fail'), ('FLAG', 'Flag')])
    resource_adequacy = serializers.ChoiceField(choices=[('PASS', 'Pass'), ('FAIL', 'Fail'), ('FLAG', 'Flag')])
    department_alignment = serializers.ChoiceField(choices=[('PASS', 'Pass'), ('FAIL', 'Fail'), ('FLAG', 'Flag')])
    comments = serializers.CharField(required=False, allow_blank=True)


class ProposalVettingDetailSerializer(serializers.Serializer):
    """Response serializer for vetting details"""
    vetting_id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    vetted_by = serializers.CharField()
    vetting_date = serializers.DateTimeField()
    technical_feasibility = serializers.CharField()
    academic_relevance = serializers.CharField()
    resource_adequacy = serializers.CharField()
    department_alignment = serializers.CharField()
    comments = serializers.CharField()
    status = serializers.CharField()
    vetting_completed_date = serializers.DateTimeField()


class VettingRevertSerializer(serializers.Serializer):
    """Serializer for HOD to revert vetting"""
    reason = serializers.CharField(required=True, min_length=10)


# ============================================================================
# UC-013: DEPARTMENT PROJECTS SERIALIZERS
# ============================================================================

class DepartmentProjectListSerializer(serializers.Serializer):
    """Serializer for HOD department projects list"""
    project_id = serializers.IntegerField()
    title = serializers.CharField()
    pi_name = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    status = serializers.CharField()
    hod_vetting_status = serializers.CharField()
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    department = serializers.CharField()


class DepartmentProjectsResponseSerializer(serializers.Serializer):
    """Response for department projects list"""
    total_projects = serializers.IntegerField()
    vetting_pending_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    projects = DepartmentProjectListSerializer(many=True)


class PendingVettingProjectSerializer(serializers.Serializer):
    """Serializer for projects pending HOD vetting"""
    project_id = serializers.IntegerField()
    title = serializers.CharField()
    pi_name = serializers.CharField()
    submitted_date = serializers.DateTimeField()
    status = serializers.CharField()
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    description = serializers.CharField()


class DepartmentSummarySerializer(serializers.Serializer):
    """Serializer for HOD department summary dashboard"""
    submitted = serializers.IntegerField()
    vetted = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    ongoing = serializers.IntegerField()
    vetting_pending = serializers.IntegerField()
    total_projects = serializers.IntegerField()
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    sanctioned_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    department = serializers.CharField()
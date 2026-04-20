"""
RSPC Staff Management Serializers (UC-007, UC-008, UC-026, UC-027)
Handles serialization for staff requests, committees, verdicts, and workflows
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from applications.globals.models import ExtraInfo, Faculty
from applications.research_procedures.models import (
    Staff, Committee, CommitteeVerdict, CommitteeMember, Project, StaffApprovalStatus,
    CommitteeDecision, StaffType
)


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal User serializer for nested representations"""
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')


class ExtraInfoSerializer(serializers.ModelSerializer):
    """ExtraInfo serializer with user details"""
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = ExtraInfo
        fields = ('id', 'user', 'user_id', 'user_type', 'department')


class CommitteeVerdictSerializer(serializers.ModelSerializer):
    """
    Committee member verdict serializer
    Used for recording APPROVE/REJECT/ABSTAIN decisions
    """
    member_name = serializers.CharField(source='member.user.get_full_name', read_only=True)
    member_username = serializers.CharField(source='member.user.username', read_only=True)
    decision_display = serializers.CharField(source='get_decision_display', read_only=True)
    
    class Meta:
        model = CommitteeVerdict
        fields = (
            'verdict_id', 'committee', 'member', 'member_name', 'member_username',
            'decision', 'decision_display', 'comments', 'timestamp'
        )
        read_only_fields = ('verdict_id', 'timestamp')


class CommitteeSerializer(serializers.ModelSerializer):
    """
    Committee serializer with members and verdicts
    Manages staff selection committee (UC-026)
    """
    members_count = serializers.SerializerMethodField()
    verdicts = CommitteeVerdictSerializer(
        source='committeeverdict_set',
        many=True,
        read_only=True
    )
    approved_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Committee
        fields = (
            'committee_id', 'name', 'members', 'members_count',
            'deadline', 'verdicts', 'approved_count', 'pending_count',
            'staff', 'created_at'
        )
        read_only_fields = ('committee_id', 'created_at', 'verdicts')
    
    def get_members_count(self, obj):
        return obj.members.count()
    
    def get_approved_count(self, obj):
        return obj.committeeverdict_set.filter(decision=CommitteeDecision.APPROVE).count()
    
    def get_pending_count(self, obj):
        return obj.committeeverdict_set.filter(decision__isnull=True).count()


class StaffListSerializer(serializers.ModelSerializer):
    """Staff list serializer with key information"""
    project_name = serializers.CharField(source='pid.name', read_only=True)
    pi_name = serializers.CharField(source='pid.pi_name', read_only=True)
    approval_status_display = serializers.CharField(
        source='get_approval_status_display',
        read_only=True
    )
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    committee = CommitteeSerializer(read_only=True)
    
    class Meta:
        model = Staff
        fields = (
            'sid', 'pid', 'project_name', 'pi_name',
            'person', 'type', 'type_display',
            'salary', 'start_date', 'duration',
            'approval_status', 'approval_status_display',
            'current_approver', 'submission_date',
            'committee', 'created_at'
        )
        read_only_fields = (
            'sid', 'approval_status_display', 'type_display', 'created_at'
        )


class StaffDetailSerializer(serializers.ModelSerializer):
    """Staff detail serializer with all information"""
    project = serializers.PrimaryKeyRelatedField(
        source='pid',
        queryset=Project.objects.all()
    )
    project_details = serializers.SerializerMethodField()
    approval_status_display = serializers.CharField(
        source='get_approval_status_display',
        read_only=True
    )
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    committee = CommitteeSerializer(read_only=True)
    approval_chain = serializers.JSONField(read_only=True)
    
    class Meta:
        model = Staff
        fields = (
            'sid', 'pid', 'project', 'project_details',
            'person', 'uname', 'type', 'type_display',
            'biodata_number', 'start_date', 'duration',
            'eligibility', 'salary', 'salary_per_month',
            'has_funds', 'post_on_website',
            'submission_date', 'interview_date', 'test_date',
            'test_mode', 'interview_place',
            'selection_committee', 'candidates_applied',
            'candidates_called', 'candidates_interviewed',
            'final_selection', 'waiting_list',
            'biodata_final', 'biodata_waiting',
            'ad_file', 'comparative_file', 'joining_report',
            'id_card', 'doc_approval',
            'approval', 'gave_verdict', 'current_approver',
            'approval_status', 'approval_status_display',
            'approval_chain', 'committee',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'sid', 'approval_status_display', 'type_display',
            'approval_chain', 'committee', 'created_at', 'updated_at'
        )
    
    def get_project_details(self, obj):
        return {
            'pid': obj.pid.pid,
            'name': obj.pid.name,
            'pi_id': obj.pid.pi_id,
            'pi_name': obj.pid.pi_name,
            'dept': obj.pid.dept
        }


class StaffCreateSerializer(serializers.ModelSerializer):
    """
    Staff creation serializer for staff requests (UC-007)
    Used by PI to create staff requests
    """
    project_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Staff
        fields = (
            'project_id', 'person', 'uname', 'biodata_number',
            'type', 'salary', 'start_date', 'duration',
            'eligibility', 'has_funds', 'post_on_website'
        )
    
    def create(self, validated_data):
        project_id = validated_data.pop('project_id')
        project = Project.objects.get(pid=project_id)
        
        staff = Staff.objects.create(
            pid=project,
            approval_status=StaffApprovalStatus.DRAFT,
            submission_date=None,
            **validated_data
        )
        return staff


class StaffApprovalSerializer(serializers.Serializer):
    """
    Serializer for staff approval actions
    Used for HOD and RSPC approval endpoints
    """
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT', 'REQUEST_INFO'])
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate_comments(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Comments must be at least 3 characters long")
        return value


class CommitteeCreateSerializer(serializers.Serializer):
    """
    Serializer for creating committee for staff review (UC-026)
    Ensures minimum 3 PI-eligible members (BR-RSPC-12)
    """
    staff_id = serializers.IntegerField()
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=3,
        help_text="ExtraInfo IDs of committee members (min 3 PI-eligible)"
    )
    deadline = serializers.DateTimeField()
    name = serializers.CharField(
        max_length=200,
        required=False,
        default="Staff Selection Committee"
    )
    
    def validate_member_ids(self, value):
        """BR-RSPC-12: Validate at least 3 members, all PI-eligible"""
        if len(value) < 3:
            raise serializers.ValidationError("Committee must have at least 3 members (BR-RSPC-12)")
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate member IDs not allowed")
        
        # Check all members are PI-eligible (Professor/Assoc Prof/Asst Prof)
        from applications.globals.models import HoldsDesignation
        
        PI_ELIGIBLE_DESIGNATIONS = ['Professor', 'Associate Professor', 'Assistant Professor', 'Assoc. Prof', 'Asst. Prof']
        
        non_eligible = []
        for member_id in value:
            try:
                extra_info = ExtraInfo.objects.get(id=member_id)
                designations = HoldsDesignation.objects.filter(
                    extra_info=extra_info
                ).values_list('designation__designation_name', flat=True)
                
                is_eligible = any(d in PI_ELIGIBLE_DESIGNATIONS for d in designations)
                if not is_eligible:
                    non_eligible.append(member_id)
            except ExtraInfo.DoesNotExist:
                raise serializers.ValidationError(f"ExtraInfo with ID {member_id} not found")
        
        if non_eligible:
            raise serializers.ValidationError(
                f"Members {non_eligible} are not PI-eligible (must be Professor/Assoc/Asst Prof) (BR-RSPC-12)"
            )
        
        return value
    
    def validate_deadline(self, value):
        """Validate deadline is in the future"""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Deadline must be in the future")
        return value


class VerdictSubmitSerializer(serializers.Serializer):
    """
    Serializer for committee member verdict submission (UC-008)
    Records APPROVE/REJECT/ABSTAIN decision with comments
    Supports conflict of interest declaration (BR-RSPC-15)
    """
    decision = serializers.ChoiceField(choices=CommitteeDecision.choices, required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_blank=True, max_length=500)
    has_conflict_of_interest = serializers.BooleanField(required=False, default=False)
    conflict_reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate(self, data):
        """BR-RSPC-15: Conflict of interest blocks verdict submission"""
        if data.get('has_conflict_of_interest'):
            if not data.get('conflict_reason'):
                raise serializers.ValidationError("Conflict reason must be provided if conflict exists (BR-RSPC-15)")
            # Cannot submit verdict if conflict exists
            data['decision'] = None
        else:
            if not data.get('decision'):
                raise serializers.ValidationError("Decision must be provided if no conflict of interest")
        
        return data


class SelectionReportSerializer(serializers.Serializer):
    """
    Serializer for final selection report (UC-027)
    Used to generate appointment report after RSPC approval
    """
    selected_candidates = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of selected candidates with details"
    )
    joining_report = serializers.FileField(required=True)
    appointment_letter_template = serializers.FileField(required=False)
    
    def validate_selected_candidates(self, value):
        """Validate selected candidates have required fields"""
        required_fields = ['name', 'designation', 'offer_date', 'stipend']
        for candidate in value:
            missing = [f for f in required_fields if f not in candidate]
            if missing:
                raise serializers.ValidationError(
                    f"Candidate missing fields: {missing}"
                )
        return value


class StaffWorkflowSerializer(serializers.Serializer):
    """
    Serializer for staff workflow status and history
    Shows current stage and approval chain
    """
    staff_id = serializers.IntegerField(read_only=True)
    current_stage = serializers.CharField()
    stage_display = serializers.CharField()
    current_approver = serializers.CharField()
    approval_chain = serializers.JSONField()
    pending_approvals = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )
    can_submit = serializers.BooleanField(read_only=True)
    next_step = serializers.CharField(read_only=True)


class CommitteeMemberSerializer(serializers.ModelSerializer):
    """Serializer for committee members (BR-RSPC-12)"""
    member_name = serializers.CharField(source='member.user.get_full_name', read_only=True)
    member_username = serializers.CharField(source='member.user.username', read_only=True)
    
    class Meta:
        model = CommitteeMember
        fields = (
            'id', 'committee', 'member', 'member_name', 'member_username',
            'appointed_date', 'is_pi_eligible', 'designation', 'department'
        )
        read_only_fields = ('id', 'appointed_date')


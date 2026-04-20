"""
UC-021/022/023 & BR-020: Serializers for Small Fund Requests, Disbursements, and Consultancy Limits
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from ..models import (
    SmallFundRequest, FundDisbursement, ConsultancyLimit,
    SmallFundRequestStatus, DisbursementStatus, Project
)


# ============================================================================
# UC-021/022: SMALL FUND REQUEST SERIALIZERS
# ============================================================================

class SmallFundRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/drafting small fund requests"""
    
    class Meta:
        model = SmallFundRequest
        fields = ('title', 'description', 'amount', 'purpose', 'justification', 'attachment_url', 'project')
        
    def validate_amount(self, value):
        """Validate amount is within 50K limit"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        if value > Decimal('50000'):
            raise serializers.ValidationError("Amount cannot exceed ₹50,000")
        return value
    
    def validate_title(self, value):
        """Validate title is not empty"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Title cannot be empty")
        return value.strip()


class SmallFundRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing small fund requests with summarized information"""
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    
    class Meta:
        model = SmallFundRequest
        fields = (
            'request_id', 'title', 'amount', 'status', 'requested_by_name',
            'submitted_date', 'approval_date', 'approved_by_name', 'project_name', 'created_date'
        )
        read_only_fields = fields


class SmallFundRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for small fund request with all information"""
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    
    class Meta:
        model = SmallFundRequest
        fields = '__all__'
        read_only_fields = (
            'request_id', 'created_date', 'modified_date', 'submission_date',
            'approval_date', 'approved_by', 'rejection_reason'
        )


class SmallFundRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating draft small fund requests"""
    
    class Meta:
        model = SmallFundRequest
        fields = ('title', 'description', 'amount', 'purpose', 'justification', 'attachment_url', 'project')
    
    def validate_amount(self, value):
        """Validate amount is within 50K limit"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        if value > Decimal('50000'):
            raise serializers.ValidationError("Amount cannot exceed ₹50,000")
        return value
    
    def validate(self, data):
        """Ensure only drafts can be updated"""
        request_obj = self.instance
        if request_obj.status != SmallFundRequestStatus.DRAFT:
            raise serializers.ValidationError(
                f"Can only update DRAFT requests. Current status: {request_obj.status}"
            )
        return data


class SmallFundApprovalSerializer(serializers.Serializer):
    """Serializer for approving/rejecting small fund requests"""
    rejection_reason = serializers.CharField(
        required=False, allow_blank=True, max_length=500,
        help_text="Reason for rejection (required if rejecting)"
    )
    
    def validate(self, data):
        # Validation will be done in view based on action
        return data


# ============================================================================
# UC-023: FUND DISBURSEMENT SERIALIZERS
# ============================================================================

class FundDisbursementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating fund disbursement"""
    
    class Meta:
        model = FundDisbursement
        fields = (
            'disbursement_date', 'amount', 'method', 'reference_number',
            'recipient_bank_account', 'remarks'
        )
    
    def validate_amount(self, value):
        """Validate disbursement amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class FundDisbursementDetailSerializer(serializers.ModelSerializer):
    """Detailed disbursement information"""
    request_title = serializers.CharField(source='request.title', read_only=True)
    request_status = serializers.CharField(source='request.status', read_only=True)
    
    class Meta:
        model = FundDisbursement
        fields = '__all__'
        read_only_fields = ('id', 'created_date')


class FundDisbursementListSerializer(serializers.ModelSerializer):
    """List view for fund disbursements"""
    request_title = serializers.CharField(source='request.title', read_only=True)
    request_amount = serializers.DecimalField(
        source='request.amount', read_only=True, max_digits=10, decimal_places=2
    )
    
    class Meta:
        model = FundDisbursement
        fields = (
            'id', 'request_title', 'request_amount', 'amount', 'method',
            'status', 'disbursement_date', 'reference_number'
        )
        read_only_fields = fields


# ============================================================================
# BR-020: CONSULTANCY LIMIT SERIALIZERS
# ============================================================================

class ConsultancyLimitSerializer(serializers.ModelSerializer):
    """Serializer for consultancy workload limits"""
    
    class Meta:
        model = ConsultancyLimit
        fields = (
            'id', 'max_consultancy_hours_per_year', 'max_consultancy_percentage',
            'max_concurrent_consultancies', 'updated_at'
        )
    
    def validate_max_consultancy_hours_per_year(self, value):
        if value <= 0:
            raise serializers.ValidationError("Max hours must be greater than 0")
        if value > 10000:
            raise serializers.ValidationError("Max hours seems too high (max 10000)")
        return value
    
    def validate_max_consultancy_percentage(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError("Percentage must be between 0 and 100")
        return value
    
    def validate_max_concurrent_consultancies(self, value):
        if value <= 0:
            raise serializers.ValidationError("Max concurrent must be at least 1")
        if value > 10:
            raise serializers.ValidationError("Max concurrent seems too high (max 10)")
        return value


class FacultyWorkloadSerializer(serializers.Serializer):
    """Serializer for faculty consultancy workload information"""
    total_consultancy_hours = serializers.IntegerField(read_only=True)
    max_allowed_hours = serializers.IntegerField(read_only=True)
    hours_utilization_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    active_consultancies = serializers.IntegerField(read_only=True)
    max_concurrent = serializers.IntegerField(read_only=True)
    workload_alerts = serializers.ListField(child=serializers.CharField(), read_only=True)


class ConsultancyValidationSerializer(serializers.Serializer):
    """Serializer for consultancy limit validation"""
    faculty_id = serializers.CharField(help_text="Faculty username/ID")
    estimated_hours = serializers.IntegerField(help_text="Estimated consultancy hours")
    
    def validate_estimated_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError("Hours must be greater than 0")
        if value > 10000:
            raise serializers.ValidationError("Hours seem too high")
        return value


class ConsultancyValidationResponseSerializer(serializers.Serializer):
    """Response for consultancy validation"""
    can_accept = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    workload = FacultyWorkloadSerializer()


class ConsultancyProjectSerializer(serializers.ModelSerializer):
    """Serializer for consultancy-type projects"""
    pi_name = serializers.CharField(source='pi_name', read_only=True)
    
    class Meta:
        model = Project
        fields = (
            'pid', 'name', 'pi_id', 'pi_name', 'description', 'project_type',
            'estimated_hours', 'hourly_rate', 'total_budget', 'status',
            'created_at'
        )
        read_only_fields = ('pid', 'created_at')

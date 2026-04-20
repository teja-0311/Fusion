"""
RSPC Expenditure Serializers (UC-012, UC-013, BR-RSPC-13)
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Expenditure, ExpenditureApprovalHistory, ExpenditureStatus, CurrentApprover
from .expenditure_services import ExpenditureValidationService


class ExpenditureApprovalHistorySerializer(serializers.ModelSerializer):
    """Serialize expenditure approval history"""
    approver_name = serializers.CharField(source='approver.user.get_full_name', read_only=True)
    
    class Meta:
        model = ExpenditureApprovalHistory
        fields = ['ahid', 'approver', 'approver_name', 'approver_role', 'action', 'comments', 'approved_at']
        read_only_fields = ['ahid', 'approved_at']


class ExpenditureCreateSerializer(serializers.Serializer):
    """
    Create expenditure request (UC-012)
    
    Validations:
    - Amount positive
    - Category valid
    - Purpose ≥ 20 chars
    - Budget sufficient
    - Supporting docs if > ₹50K
    """
    project_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[
        'MANPOWER', 'EQUIPMENT', 'CONSUMABLES', 'TRAVEL', 'CONTINGENCY', 'OVERHEAD', 'OTHER'
    ])
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0.01)
    purpose = serializers.CharField(min_length=20, max_length=5000)
    supporting_documents = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )


class ExpenditureListSerializer(serializers.ModelSerializer):
    """
    List expenditures (UC-013)
    
    Role-based filtering:
    - PI: Own expenditures
    - HOD: Department expenditures pending HOD approval
    - RSPC: All expenditures
    """
    requested_by_name = serializers.CharField(source='requested_by.user.get_full_name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    approval_tier = serializers.SerializerMethodField()
    days_pending = serializers.SerializerMethodField()
    
    class Meta:
        model = Expenditure
        fields = [
            'eid', 'project', 'project_name', 'category', 'amount', 'purpose',
            'status', 'current_approver', 'current_stage', 'requested_by_name',
            'request_date', 'approval_tier', 'days_pending'
        ]
        read_only_fields = ['eid', 'request_date', 'status', 'current_approver']
    
    def get_approval_tier(self, obj):
        """Get approval tier (1, 2, or 3)"""
        return obj.get_approval_tier()
    
    def get_days_pending(self, obj):
        """Calculate days since request"""
        from datetime import datetime
        now = datetime.now(obj.request_date.tzinfo) if obj.request_date.tzinfo else datetime.now()
        delta = now - obj.request_date
        return delta.days


class ExpenditureDetailSerializer(serializers.ModelSerializer):
    """
    Detailed expenditure view
    
    Includes:
    - Full approval chain history
    - Budget validation
    - Approval workflow status
    """
    requested_by_name = serializers.CharField(source='requested_by.user.get_full_name', read_only=True)
    requested_by_email = serializers.CharField(source='requested_by.user.email', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    approval_history = ExpenditureApprovalHistorySerializer(many=True, read_only=True, source='approval_history')
    approval_tier = serializers.SerializerMethodField()
    remaining_budget = serializers.SerializerMethodField()
    
    class Meta:
        model = Expenditure
        fields = [
            'eid', 'project', 'project_name', 'category', 'amount', 'purpose',
            'status', 'current_approver', 'current_stage', 'requested_by',
            'requested_by_name', 'requested_by_email', 'request_date',
            'approval_chain', 'approval_history', 'supporting_documents',
            'approval_tier', 'remaining_budget', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'eid', 'request_date', 'status', 'current_approver', 'approval_chain',
            'created_at', 'updated_at'
        ]
    
    def get_approval_tier(self, obj):
        """Get approval tier (1, 2, or 3)"""
        return obj.get_approval_tier()
    
    def get_remaining_budget(self, obj):
        """Calculate remaining budget for category"""
        if hasattr(obj.project, 'budget') and obj.project.budget:
            budget = obj.project.budget
            category_budget = budget.get_category_budget(obj.category)
            category_util = budget.get_category_utilization(obj.category)
            return float(category_budget - category_util)
        return None


class ExpenditureApproveSerializer(serializers.Serializer):
    """Approve expenditure request"""
    expenditure_id = serializers.IntegerField()
    approver_role = serializers.ChoiceField(choices=['PI', 'HOD', 'RSPC'])
    comments = serializers.CharField(required=False, default="", allow_blank=True)


class ExpenditureRejectSerializer(serializers.Serializer):
    """Reject expenditure request"""
    expenditure_id = serializers.IntegerField()
    rejecter_role = serializers.ChoiceField(choices=['PI', 'HOD', 'RSPC'])
    reason = serializers.CharField(min_length=10, max_length=1000)

"""
Serializers for UC-017, UC-018, BR-015 implementations
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from datetime import datetime

from ..models import (
    StipendDisbursement, StipendBatch,
    ComplianceReport,
    ProjectClosure, Staff
)


# ============================================================================
# UC-017: STIPEND DISBURSEMENT SERIALIZERS
# ============================================================================

class StipendDisbursementSerializer(serializers.ModelSerializer):
    """Serializer for individual stipend disbursement records"""
    staff_name = serializers.CharField(source='staff.person', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    
    class Meta:
        model = StipendDisbursement
        fields = [
            'id', 'staff', 'staff_name', 'project', 'project_title',
            'month', 'stipend_amount', 'status', 'disbursement_date',
            'payment_method', 'payment_reference', 'remarks',
            'created_date', 'modified_date'
        ]
        read_only_fields = ['created_date', 'modified_date']


class StipendBatchSerializer(serializers.ModelSerializer):
    """Serializer for stipend batch"""
    project_title = serializers.CharField(source='project.title', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    disbursements = StipendDisbursementSerializer(
        source='stipenddisbursement_set',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = StipendBatch
        fields = [
            'id', 'batch_date', 'project', 'project_title', 'month',
            'total_amount', 'status', 'disbursement_count',
            'approved_by', 'approved_by_name', 'approval_date',
            'created_date', 'disbursements'
        ]
        read_only_fields = ['batch_date', 'created_date']


class StipendBatchCreateSerializer(serializers.Serializer):
    """Serializer for creating stipend batch"""
    project_id = serializers.IntegerField()
    month = serializers.CharField(help_text="Format: YYYY-MM-01")


class StipendBatchApprovalSerializer(serializers.Serializer):
    """Serializer for batch approval"""
    # No extra fields needed - just uses standard approval


class StipendHistorySerializer(serializers.Serializer):
    """Serializer for staff stipend history"""
    month = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    status = serializers.CharField()
    payment_reference = serializers.CharField()
    payment_method = serializers.CharField()
    disbursement_date = serializers.DateTimeField(required=False, allow_null=True)


# ============================================================================
# UC-018: COMPLIANCE REPORT SERIALIZERS
# ============================================================================

class ComplianceReportListSerializer(serializers.ModelSerializer):
    """Serializer for compliance report list"""
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = ComplianceReport
        fields = [
            'id', 'report_date', 'report_type', 'status',
            'period_start', 'period_end', 'compliance_percentage',
            'total_items_checked', 'compliant_items', 'non_compliant_items',
            'generated_by', 'generated_by_name', 'created_date'
        ]
        read_only_fields = ['report_date', 'created_date']


class ComplianceReportDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed compliance report"""
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    findings = serializers.SerializerMethodField()
    
    class Meta:
        model = ComplianceReport
        fields = [
            'id', 'report_date', 'report_type', 'status',
            'period_start', 'period_end', 'compliance_percentage',
            'total_items_checked', 'compliant_items', 'non_compliant_items',
            'generated_by', 'generated_by_name', 'notes',
            'report_content', 'export_formats', 'findings',
            'created_date'
        ]
        read_only_fields = ['report_date', 'created_date']
    
    def get_findings(self, obj):
        """Extract findings from report_content"""
        if isinstance(obj.report_content, dict):
            return obj.report_content.get('findings', [])
        return []


class ComplianceReportGenerateSerializer(serializers.Serializer):
    """Serializer for generating compliance report"""
    report_type = serializers.ChoiceField(choices=['BUDGET', 'EXPENDITURE', 'STAFF', 'PROJECT', 'FULL'])
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class ComplianceReportExportSerializer(serializers.Serializer):
    """Serializer for report export"""
    format = serializers.ChoiceField(choices=['pdf', 'xlsx'])


# ============================================================================
# BR-015: SETTLEMENT SERIALIZERS
# ============================================================================

class ProjectClosureSettlementSerializer(serializers.ModelSerializer):
    """Serializer for project closure settlement"""
    project_title = serializers.CharField(source='project.title', read_only=True)
    project_pi = serializers.CharField(source='project.pi.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = ProjectClosure
        fields = [
            'closure_id', 'project', 'project_title', 'project_pi',
            'status', 'settlement_amount', 'held_amount', 'refund_amount',
            'penalty_amount', 'settlement_calculated', 'settlement_approved',
            'created_date', 'modified_date'
        ]
        read_only_fields = ['closure_id', 'created_date', 'modified_date']


class SettlementCalculationSerializer(serializers.Serializer):
    """Serializer for settlement calculation response"""
    settlement_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    held_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    refund_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    penalties = serializers.DecimalField(max_digits=15, decimal_places=2)
    compliance_deductions = serializers.DecimalField(max_digits=15, decimal_places=2)
    doc_deductions = serializers.DecimalField(max_digits=15, decimal_places=2)
    budget_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    expenditure_total = serializers.DecimalField(max_digits=15, decimal_places=2)


class SettlementApprovalSerializer(serializers.Serializer):
    """Serializer for settlement approval"""
    closure_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    settlement_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

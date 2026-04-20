"""
UC-006 and UC-010: Progress and Project Closure Report Serializers
"""

from rest_framework import serializers
from ..models import ProgressReport, ProjectClosure, Project


class ProgressReportCreateSerializer(serializers.Serializer):
    """Create/Submit progress report (UC-006)"""
    project_id = serializers.IntegerField()
    report_period = serializers.ChoiceField(choices=['QUARTERLY', 'HALF_YEARLY', 'ANNUAL', 'FINAL'])
    report_content = serializers.CharField(min_length=50)
    challenges_faced = serializers.CharField(min_length=20)
    milestones_achieved = serializers.CharField(min_length=20)
    publications_filed = serializers.IntegerField(min_value=0, default=0)
    recommendations = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.FileField(required=False, allow_null=True)


class ProgressReportListSerializer(serializers.ModelSerializer):
    """List progress reports"""
    class Meta:
        model = ProgressReport
        fields = ['prid', 'project', 'report_period', 'status', 'submitted_by', 'submitted_date', 'created_date']


class ProgressReportDetailSerializer(serializers.ModelSerializer):
    """Detailed progress report view"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.username', read_only=True)
    
    class Meta:
        model = ProgressReport
        fields = [
            'prid', 'project', 'project_name', 'report_period', 'submitted_by', 
            'submitted_by_name', 'report_content', 'challenges_faced', 'milestones_achieved',
            'publications_filed', 'recommendations', 'attachments', 'status', 
            'reviewer_comments', 'submitted_date', 'created_date', 'modified_date'
        ]


class ProgressReportActionSerializer(serializers.Serializer):
    """Action on progress report (review, approve, reject)"""
    action = serializers.ChoiceField(choices=['review', 'approve', 'reject'])
    comments = serializers.CharField(required=False, allow_blank=True)


class ProjectClosureCreateSerializer(serializers.Serializer):
    """Create/Submit project closure (UC-010)"""
    project_id = serializers.IntegerField()
    final_report = serializers.CharField(min_length=50)
    deliverables_summary = serializers.CharField(min_length=20)
    challenges_summary = serializers.CharField(min_length=20)
    lessons_learned = serializers.CharField(min_length=20)
    publications_generated = serializers.IntegerField(min_value=0, default=0)
    patents_filed = serializers.IntegerField(min_value=0, default=0)
    utilization_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    outstanding_items = serializers.CharField(required=False, allow_blank=True)
    final_settlement_document = serializers.FileField(required=False, allow_null=True)


class ProjectClosureDetailSerializer(serializers.ModelSerializer):
    """Detailed project closure view"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    closed_by_name = serializers.CharField(source='closed_by.username', read_only=True)
    
    class Meta:
        model = ProjectClosure
        fields = [
            'closure_id', 'project', 'project_name', 'closed_by', 'closed_by_name',
            'final_report', 'deliverables_summary', 'challenges_summary', 
            'lessons_learned', 'publications_generated', 'patents_filed',
            'utilization_percentage', 'final_settlement_document', 'outstanding_items',
            'status', 'closure_date', 'created_date', 'modified_date'
        ]


class ProjectClosureActionSerializer(serializers.Serializer):
    """Action on project closure (verify, settle, approve)"""
    action = serializers.ChoiceField(choices=['verify', 'settle', 'close'])
    comments = serializers.CharField(required=False, allow_blank=True)


class PendingApprovalsSerializer(serializers.Serializer):
    """Pending approvals for dashboard (BR-018)"""
    id = serializers.IntegerField()
    entity_type = serializers.CharField()
    entity_name = serializers.CharField()
    deadline = serializers.DateTimeField()
    days_remaining = serializers.IntegerField()
    urgency = serializers.CharField()  # RED, YELLOW, GREEN
    created_date = serializers.DateTimeField()

"""
UC-006 and UC-010: Progress and Project Closure Report Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from ..models import (
    ProgressReport, ProjectClosure, Project, ApprovalSLA, 
    ProgressReportStatus, ProjectClosureStatus, ApprovalSLAEntityType
)
from .report_serializers import (
    ProgressReportCreateSerializer, ProgressReportListSerializer, ProgressReportDetailSerializer,
    ProgressReportActionSerializer, ProjectClosureCreateSerializer, ProjectClosureDetailSerializer,
    ProjectClosureActionSerializer, PendingApprovalsSerializer
)
from ..notification_service import NotificationService


class ProgressReportViewSet(viewsets.ViewSet):
    """UC-006: Progress Report Submission and Management"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /rspc/reports/progress/ - List progress reports"""
        user = request.user
        
        # Get project_id and status filters
        project_id = request.query_params.get('project_id')
        report_status = request.query_params.get('status')
        period = request.query_params.get('period')
        
        # Build query
        queryset = ProgressReport.objects.all()
        
        # Role-based filtering
        if not self._is_admin_or_director(user):
            # PI sees only their own projects
            queryset = queryset.filter(project__pi_id=user.username)
        
        # Apply filters
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if report_status:
            queryset = queryset.filter(status=report_status)
        if period:
            queryset = queryset.filter(report_period=period)
        
        serializer = ProgressReportListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def submit(self, request):
        """POST /rspc/reports/progress/submit/ - Submit progress report (UC-006)"""
        serializer = ProgressReportCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            validated_data = serializer.validated_data
            project = get_object_or_404(Project, pid=validated_data['project_id'])
            
            # Permission check: PI only
            if project.pi_id != request.user.username:
                return Response(
                    {'detail': 'Only PI can submit progress reports'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # BR-012: Check report frequency (can't submit same period twice)
            existing = ProgressReport.objects.filter(
                project=project,
                report_period=validated_data['report_period'],
                status__in=['SUBMITTED', 'REVIEWED', 'APPROVED']
            ).exists()
            
            if existing:
                return Response(
                    {'detail': f"Progress report for {validated_data['report_period']} already submitted"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # BR-013: Check completeness (all required fields present)
            required_fields = ['report_content', 'challenges_faced', 'milestones_achieved']
            for field in required_fields:
                if not validated_data.get(field):
                    return Response(
                        {'detail': f'Field {field} is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create report
            report = ProgressReport.objects.create(
                project=project,
                report_period=validated_data['report_period'],
                submitted_by=request.user,
                report_content=validated_data['report_content'],
                challenges_faced=validated_data['challenges_faced'],
                milestones_achieved=validated_data['milestones_achieved'],
                publications_filed=validated_data.get('publications_filed', 0),
                recommendations=validated_data.get('recommendations', ''),
                attachments=validated_data.get('attachments'),
                status=ProgressReportStatus.SUBMITTED,
                submitted_date=timezone.now()
            )
            
            # Trigger notification to RSPC Admin & Director
            NotificationService.notify_progress_report_submitted(project, report)
            
            return Response({
                'report_id': report.prid,
                'status': report.status,
                'submission_date': report.submitted_date
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def retrieve(self, request, pk=None):
        """GET /rspc/reports/progress/{report_id}/ - Get report details"""
        report = get_object_or_404(ProgressReport, prid=pk)
        
        # Permission check
        if not self._can_view_report(request.user, report):
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProgressReportDetailSerializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """POST /rspc/reports/progress/{report_id}/action/ - Review/approve/reject"""
        report = get_object_or_404(ProgressReport, prid=pk)
        
        # Permission check: RSPC Admin or Director only
        if not self._is_admin_or_director(request.user):
            return Response(
                {'detail': 'Only RSPC Admin or Director can approve reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProgressReportActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        action_type = serializer.validated_data['action']
        comments = serializer.validated_data.get('comments', '')
        
        if action_type == 'review':
            report.status = ProgressReportStatus.REVIEWED
            report.reviewer_comments = comments
            report.save()
            NotificationService.notify_progress_report_reviewed(report)
        
        elif action_type == 'approve':
            report.status = ProgressReportStatus.APPROVED
            report.reviewer_comments = comments
            report.save()
            NotificationService.notify_progress_report_approved(report)
        
        elif action_type == 'reject':
            report.status = ProgressReportStatus.REJECTED
            report.reviewer_comments = comments
            report.save()
            NotificationService.notify_progress_report_rejected(report)
        
        return Response({
            'report_id': report.prid,
            'status': report.status,
            'message': f'Report {action_type} successfully'
        }, status=status.HTTP_200_OK)
    
    @staticmethod
    def _is_admin_or_director(user):
        """Check if user is RSPC Admin or Director"""
        # Check for user roles in ExtraInfo or permissions
        try:
            from applications.globals.models import ExtraInfo
            extra = ExtraInfo.objects.filter(user=user).first()
            if extra and extra.designation and extra.designation.name in ['RSPC Admin', 'Director', 'RSPC_ADMIN']:
                return True
        except:
            pass
        return False
    
    @staticmethod
    def _can_view_report(user, report):
        """Check if user can view the report"""
        if ProgressReportViewSet._is_admin_or_director(user):
            return True
        if report.project.pi_id == user.username:
            return True
        return False


class ProjectClosureViewSet(viewsets.ViewSet):
    """UC-010: Project Closure Submission and Management"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/closure')
    def submit(self, request, project_id=None):
        """POST /rspc/projects/{project_id}/closure/ - Submit closure report (UC-010)"""
        project = get_object_or_404(Project, pid=project_id)
        
        # Permission check: PI only
        if project.pi_id != request.user.username:
            return Response(
                {'detail': 'Only PI can submit closure report'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProjectClosureCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Validation: Project must be in ONGOING/EXTENDED status
        if project.status not in ['ONGOING', 'EXTENDED']:
            return Response(
                {'detail': 'Project must be ONGOING or EXTENDED to submit closure'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # BR-014: Check project timeline (must be past end date or extension end)
        today = timezone.now().date()
        end_date = project.end_date or project.submission_date.date()
        
        if today < end_date:
            return Response(
                {'detail': 'Cannot close project before end date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # BR-016: Verify document uploads present (if required)
        validated_data = serializer.validated_data
        
        # Check if closure already exists
        existing_closure = ProjectClosure.objects.filter(project=project).first()
        if existing_closure:
            return Response(
                {'detail': 'Project closure already submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create closure report
        closure = ProjectClosure.objects.create(
            project=project,
            closed_by=request.user,
            final_report=validated_data['final_report'],
            deliverables_summary=validated_data['deliverables_summary'],
            challenges_summary=validated_data['challenges_summary'],
            lessons_learned=validated_data['lessons_learned'],
            publications_generated=validated_data.get('publications_generated', 0),
            patents_filed=validated_data.get('patents_filed', 0),
            utilization_percentage=validated_data.get('utilization_percentage', 0),
            outstanding_items=validated_data.get('outstanding_items', ''),
            final_settlement_document=validated_data.get('final_settlement_document'),
            status=ProjectClosureStatus.SUBMITTED
        )
        
        # Trigger settlement calculation & notifications
        NotificationService.notify_project_closure_submitted(project, closure)
        
        return Response({
            'closure_id': closure.closure_id,
            'status': closure.status
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='(?P<project_id>[^/.]+)/closure')
    def retrieve(self, request, project_id=None):
        """GET /rspc/projects/{project_id}/closure/ - Get closure report"""
        project = get_object_or_404(Project, pid=project_id)
        closure = get_object_or_404(ProjectClosure, project=project)
        
        # Permission check
        if not self._can_view_closure(request.user, project):
            return Response(
                {'detail': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProjectClosureDetailSerializer(closure)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/closure/approve')
    def approve(self, request, project_id=None):
        """POST /rspc/projects/{project_id}/closure/approve/ - Approve closure"""
        project = get_object_or_404(Project, pid=project_id)
        closure = get_object_or_404(ProjectClosure, project=project)
        
        serializer = ProjectClosureActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        action_type = serializer.validated_data['action']
        comments = serializer.validated_data.get('comments', '')
        
        # Permission checks by action
        if action_type == 'verify':
            # RSPC Admin can verify
            if not self._is_rspc_admin(request.user):
                return Response(
                    {'detail': 'Only RSPC Admin can verify closure'},
                    status=status.HTTP_403_FORBIDDEN
                )
            closure.status = ProjectClosureStatus.VERIFIED
        
        elif action_type == 'settle':
            # Director can settle (apply BR-015 rules)
            if not self._is_director(request.user):
                return Response(
                    {'detail': 'Only Director can settle closure'},
                    status=status.HTTP_403_FORBIDDEN
                )
            closure.status = ProjectClosureStatus.SETTLED
            # BR-015: Settlement calculation would happen here
        
        elif action_type == 'close':
            # Director can approve final closure
            if not self._is_director(request.user):
                return Response(
                    {'detail': 'Only Director can approve closure'},
                    status=status.HTTP_403_FORBIDDEN
                )
            closure.status = ProjectClosureStatus.CLOSED
            project.status = 'COMPLETED'
            project.save()
        
        closure.save()
        NotificationService.notify_project_closure_status_changed(closure)
        
        return Response({
            'closure_id': closure.closure_id,
            'status': closure.status,
            'message': f'Closure {action_type} successfully'
        }, status=status.HTTP_200_OK)
    
    @staticmethod
    def _can_view_closure(user, project):
        """Check if user can view closure"""
        try:
            from applications.globals.models import ExtraInfo
            extra = ExtraInfo.objects.filter(user=user).first()
            is_admin = extra and extra.designation and extra.designation.name in ['RSPC Admin', 'Director', 'RSPC_ADMIN']
        except:
            is_admin = False
        
        if is_admin:
            return True
        if project.pi_id == user.username:
            return True
        # HOD can view
        # Director can view
        return False
    
    @staticmethod
    def _is_rspc_admin(user):
        """Check if user is RSPC Admin"""
        try:
            from applications.globals.models import ExtraInfo
            extra = ExtraInfo.objects.filter(user=user).first()
            if extra and extra.designation and extra.designation.name in ['RSPC Admin', 'RSPC_ADMIN']:
                return True
        except:
            pass
        return False
    
    @staticmethod
    def _is_director(user):
        """Check if user is Director"""
        try:
            from applications.globals.models import ExtraInfo
            extra = ExtraInfo.objects.filter(user=user).first()
            if extra and extra.designation and extra.designation.name in ['Director', 'DIRECTOR']:
                return True
        except:
            pass
        return False


class ApprovalsViewSet(viewsets.ViewSet):
    """BR-018: Approval SLA and Pending Approvals"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """GET /rspc/approvals/pending/ - Get pending approvals for current user"""
        user = request.user
        
        # Get all pending SLAs for current user
        pending_slas = ApprovalSLA.objects.filter(
            current_approver=user,
            status='PENDING'
        ).order_by('deadline')
        
        now = timezone.now()
        results = []
        
        for sla in pending_slas:
            days_remaining = (sla.deadline - now).days
            
            # Determine urgency
            if days_remaining < 0:
                urgency = 'RED'  # Overdue
            elif days_remaining <= 1:
                urgency = 'RED'  # < 1 day
            elif days_remaining <= 3:
                urgency = 'YELLOW'  # < 3 days
            else:
                urgency = 'GREEN'  # OK
            
            # Get entity name
            entity_name = self._get_entity_name(sla)
            
            results.append({
                'id': sla.sla_id,
                'entity_type': sla.entity_type,
                'entity_name': entity_name,
                'deadline': sla.deadline,
                'days_remaining': days_remaining,
                'urgency': urgency,
                'created_date': sla.created_date
            })
        
        serializer = PendingApprovalsSerializer(results, many=True)
        return Response(serializer.data)
    
    @staticmethod
    def _get_entity_name(sla):
        """Get human-readable name for entity"""
        try:
            if sla.entity_type == 'expenditure':
                from ..models import Expenditure
                exp = Expenditure.objects.get(eid=sla.entity_id)
                return f"Expenditure: {exp.category} - ₹{exp.amount}"
            elif sla.entity_type == 'project':
                from ..models import Project
                proj = Project.objects.get(pid=sla.entity_id)
                return f"Project: {proj.name}"
            elif sla.entity_type == 'staff':
                from ..models import Staff
                st = Staff.objects.get(sid=sla.entity_id)
                return f"Staff: {st.person}"
            elif sla.entity_type == 'progress_report':
                report = ProgressReport.objects.get(prid=sla.entity_id)
                return f"Report: {report.project.name} ({report.report_period})"
            elif sla.entity_type == 'project_closure':
                closure = ProjectClosure.objects.get(closure_id=sla.entity_id)
                return f"Closure: {closure.project.name}"
        except:
            pass
        return f"{sla.entity_type} {sla.entity_id}"

"""
API views for UC-017, UC-018, BR-015 implementations
Stipend disbursement, compliance reports, and settlement calculations
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from datetime import datetime, date
from decimal import Decimal

from ..models import (
    StipendBatch, StipendDisbursement, ComplianceReport,
    ProjectClosure, Project, Staff
)
from ..stipend_service import StipendService, RSPCError as StipendError
from ..compliance_service import ComplianceService, RSPCError as ComplianceError
from ..settlement_service import SettlementService, RSPCError as SettlementError
from .stipend_compliance_serializers import (
    StipendBatchSerializer, StipendDisbursementSerializer,
    StipendBatchCreateSerializer, StipendHistorySerializer,
    ComplianceReportListSerializer, ComplianceReportDetailSerializer,
    ComplianceReportGenerateSerializer, ComplianceReportExportSerializer,
    ProjectClosureSettlementSerializer, SettlementCalculationSerializer,
    SettlementApprovalSerializer
)
from ..role_filters import get_user_role, is_rspc_admin, is_director


# ============================================================================
# UC-017: STIPEND DISBURSEMENT VIEWSET
# ============================================================================

class StipendBatchViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing stipend disbursement batches.
    Endpoints: list, retrieve, create, approve, disburse
    """
    queryset = StipendBatch.objects.all()
    serializer_class = StipendBatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['project', 'status', 'month']
    ordering_fields = ['month', 'created_date', 'status']
    ordering = ['-month']
    
    def list(self, request, *args, **kwargs):
        """
        GET /rspc/staff/stipend/batches/
        List all disbursement batches (RSPC Admin only)
        """
        if not is_rspc_admin(request.user):
            return Response(
                {'error': 'Only RSPC Admin can view batches'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /rspc/staff/stipend/batches/{batch_id}/
        View batch details with all disbursements
        """
        if not (is_rspc_admin(request.user) or is_director(request.user)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def create_batch(self, request):
        """
        POST /rspc/staff/stipend/create-batch/
        Create batch for project/month with all active staff
        """
        if not is_rspc_admin(request.user):
            return Response(
                {'error': 'Only RSPC Admin can create batches'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = StipendBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = StipendService.create_batch(
                serializer.validated_data['project_id'],
                serializer.validated_data['month']
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except StipendError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        POST /rspc/staff/stipend/batches/{batch_id}/approve/
        Approve batch for disbursement
        """
        if not (is_rspc_admin(request.user) or is_director(request.user)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            result = StipendService.approve_batch(pk, request.user)
            return Response(result, status=status.HTTP_200_OK)
        except StipendError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """
        POST /rspc/staff/stipend/batches/{batch_id}/disburse/
        Mark batch as disbursed
        """
        if not is_rspc_admin(request.user):
            return Response(
                {'error': 'Only RSPC Admin can disburse batches'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            payment_details = {
                'payment_method': request.data.get('payment_method', 'BANK'),
                'payment_reference': request.data.get('payment_reference', '')
            }
            result = StipendService.disburse_batch(pk, payment_details)
            return Response(result, status=status.HTTP_200_OK)
        except StipendError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StipendHistoryViewSet(viewsets.ViewSet):
    """
    Viewset for viewing stipend disbursement history
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='history/(?P<staff_id>[^/.]+)')
    def get_history(self, request, staff_id=None):
        """
        GET /rspc/staff/stipend/history/{staff_id}/
        View disbursement history for staff (last 12 months)
        """
        try:
            staff = Staff.objects.get(sid=staff_id)
            
            # Check permissions
            if staff.pid.pi != request.user.extrainfo and not is_rspc_admin(request.user):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            history = StipendService.get_staff_stipend_history(staff_id, limit=12)
            return Response(history, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff not found'}, status=status.HTTP_404_NOT_FOUND)
        except StipendError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='(?P<disbursement_id>[^/.]+)/mark-failed')
    def mark_failed(self, request, disbursement_id=None):
        """
        POST /rspc/staff/stipend/{disbursement_id}/mark-failed/
        Mark disbursement as failed
        """
        if not is_rspc_admin(request.user):
            return Response(
                {'error': 'Only RSPC Admin can mark as failed'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', 'No reason provided')
        
        try:
            result = StipendService.mark_disbursement_failed(disbursement_id, reason)
            return Response(result, status=status.HTTP_200_OK)
        except StipendError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# UC-018: COMPLIANCE REPORT VIEWSET
# ============================================================================

class ComplianceReportViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing compliance reports
    Endpoints: list, retrieve, generate, export, approve
    """
    queryset = ComplianceReport.objects.all()
    serializer_class = ComplianceReportListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['report_type', 'status']
    ordering_fields = ['report_date', 'compliance_percentage']
    ordering = ['-report_date']
    
    def list(self, request, *args, **kwargs):
        """
        GET /rspc/reports/compliance/
        List all compliance reports (RSPC Admin, Director only)
        """
        if not (is_rspc_admin(request.user) or is_director(request.user)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /rspc/reports/compliance/{report_id}/
        View detailed report
        """
        if not (is_rspc_admin(request.user) or is_director(request.user)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        self.serializer_class = ComplianceReportDetailSerializer
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        POST /rspc/reports/compliance/generate/
        Generate new compliance report
        """
        if not is_rspc_admin(request.user):
            return Response(
                {'error': 'Only RSPC Admin can generate reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ComplianceReportGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            report_type = serializer.validated_data['report_type']
            period_start = serializer.validated_data['period_start']
            period_end = serializer.validated_data['period_end']
            
            if report_type == 'BUDGET':
                result = ComplianceService.generate_budget_compliance(period_start, period_end, request.user)
            elif report_type == 'EXPENDITURE':
                result = ComplianceService.generate_expenditure_compliance(period_start, period_end, request.user)
            elif report_type == 'STAFF':
                result = ComplianceService.generate_staff_compliance(period_start, period_end, request.user)
            elif report_type == 'PROJECT':
                result = ComplianceService.generate_project_compliance(period_start, period_end, request.user)
            else:
                return Response({'error': 'Invalid report type'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(result, status=status.HTTP_201_CREATED)
        except ComplianceError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """
        GET /rspc/reports/compliance/{report_id}/export/?format=pdf|xlsx
        Export report as PDF or Excel
        """
        if not (is_rspc_admin(request.user) or is_director(request.user)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            report = ComplianceReport.objects.get(id=pk)
            format_type = request.query_params.get('format', 'pdf')
            
            if format_type == 'pdf':
                file_path = ComplianceService.export_to_pdf(report)
            elif format_type == 'xlsx':
                file_path = ComplianceService.export_to_excel(report)
            else:
                return Response({'error': 'Invalid format'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({'file_path': file_path}, status=status.HTTP_200_OK)
        except ComplianceReport.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        POST /rspc/reports/compliance/{report_id}/approve/
        Approve compliance report (Director only)
        """
        if not is_director(request.user):
            return Response(
                {'error': 'Only Director can approve reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            result = ComplianceService.approve_report(pk, request.user)
            return Response(result, status=status.HTTP_200_OK)
        except ComplianceError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# BR-015: SETTLEMENT VIEWSET
# ============================================================================

class ProjectSettlementViewSet(viewsets.ViewSet):
    """
    Viewset for project settlement calculations and approvals
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/closure/calculate-settlement')
    def calculate_settlement(self, request, project_id=None):
        """
        POST /rspc/projects/{project_id}/closure/calculate-settlement/
        Calculate settlement for project closure (RSPC Admin only)
        """
        if not is_rspc_admin(request.user):
            return Response(
                {'error': 'Only RSPC Admin can calculate settlement'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            result = SettlementService.calculate_settlement(project_id, request.user)
            return Response(result, status=status.HTTP_200_OK)
        except SettlementError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/closure/approve-settlement')
    def approve_settlement(self, request, project_id=None):
        """
        POST /rspc/projects/{project_id}/closure/approve-settlement/
        Approve settlement (Director only)
        """
        if not is_director(request.user):
            return Response(
                {'error': 'Only Director can approve settlement'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            result = SettlementService.approve_settlement(project_id, request.user)
            return Response(result, status=status.HTTP_200_OK)
        except SettlementError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

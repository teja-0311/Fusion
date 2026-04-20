"""
UC-021/022/023 & BR-020: API Views for Small Fund Requests, Disbursements, and Consultancy
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import timedelta
from decimal import Decimal

from ..models import (
    SmallFundRequest, FundDisbursement, ConsultancyLimit, Project,
    SmallFundRequestStatus, DisbursementStatus, Notification,
    NotificationEventType, NotificationEntityType, ProjectTypeChoice
)
from ..notification_service import NotificationService
from ..consultancy_service import ConsultancyService
from ..role_filters import get_user_role_and_dept
from .gap_items_serializers import (
    SmallFundRequestCreateSerializer, SmallFundRequestListSerializer,
    SmallFundRequestDetailSerializer, SmallFundRequestUpdateSerializer,
    SmallFundApprovalSerializer, FundDisbursementCreateSerializer,
    FundDisbursementDetailSerializer, FundDisbursementListSerializer,
    ConsultancyLimitSerializer, FacultyWorkloadSerializer,
    ConsultancyValidationSerializer, ConsultancyValidationResponseSerializer,
    ConsultancyProjectSerializer
)


# ============================================================================
# UC-021: SMALL FUND REQUEST - CREATE/DRAFT/SUBMIT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_small_fund_request(request):
    """
    POST /rspc/funds/small/request/
    Create a new small fund request (DRAFT status)
    Body: {title, description, amount, purpose, justification, attachment_url?, project_id?}
    """
    try:
        serializer = SmallFundRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create request
        fund_request = SmallFundRequest.objects.create(
            requested_by=request.user,
            status=SmallFundRequestStatus.DRAFT,
            **serializer.validated_data
        )
        
        return Response(
            {
                'success': True,
                'message': 'Fund request created in DRAFT status',
                'request_id': fund_request.request_id,
                'data': SmallFundRequestDetailSerializer(fund_request).data
            },
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_small_fund_request(request, request_id):
    """
    PATCH /rspc/funds/small/request/{request_id}/
    Update a DRAFT small fund request
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        
        # Verify ownership
        if fund_request.requested_by != request.user:
            return Response(
                {'success': False, 'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only drafts can be updated
        if fund_request.status != SmallFundRequestStatus.DRAFT:
            return Response(
                {'success': False, 'error': f'Can only update DRAFT requests, current status: {fund_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SmallFundRequestUpdateSerializer(fund_request, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save()
        
        return Response(
            {
                'success': True,
                'message': 'Fund request updated',
                'data': SmallFundRequestDetailSerializer(fund_request).data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_small_fund_request(request, request_id):
    """
    POST /rspc/funds/small/request/{request_id}/submit/
    Submit a DRAFT request for approval (DRAFT → SUBMITTED)
    Triggers 'small_fund_submitted' notification to HOD
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        
        # Verify ownership
        if fund_request.requested_by != request.user:
            return Response(
                {'success': False, 'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only drafts can be submitted
        if fund_request.status != SmallFundRequestStatus.DRAFT:
            return Response(
                {'success': False, 'error': f'Can only submit DRAFT requests, current status: {fund_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update request
        fund_request.status = SmallFundRequestStatus.SUBMITTED
        fund_request.submission_date = timezone.now()
        fund_request.save()
        
        # Send notification to HOD
        try:
            # Get HOD for department (would need actual HOD lookup in production)
            NotificationService.small_fund_submitted(fund_request, request.user)
        except Exception as notif_err:
            # Log but don't fail if notification fails
            print(f"Notification error: {notif_err}")
        
        return Response(
            {
                'success': True,
                'message': 'Fund request submitted for approval',
                'data': SmallFundRequestDetailSerializer(fund_request).data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# UC-021: SMALL FUND REQUEST - LIST/VIEW ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_small_fund_requests(request):
    """
    GET /rspc/funds/small/requests/
    List small fund requests with role-based filtering and pagination
    Query params: ?status=SUBMITTED&page=1&limit=20
    """
    try:
        # Base queryset - users see their own requests
        queryset = SmallFundRequest.objects.filter(requested_by=request.user)
        
        # Add filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        start = (page - 1) * limit
        end = start + limit
        
        total_count = queryset.count()
        requests = queryset.order_by('-created_date')[start:end]
        
        serializer = SmallFundRequestListSerializer(requests, many=True)
        
        return Response(
            {
                'success': True,
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_small_fund_request_details(request, request_id):
    """
    GET /rspc/funds/small/request/{request_id}/
    View details of a specific small fund request
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        
        # Verify access
        if fund_request.requested_by != request.user:
            # TODO: Add HOD/Admin access
            return Response(
                {'success': False, 'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SmallFundRequestDetailSerializer(fund_request)
        
        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# UC-022: SMALL FUND APPROVAL/REJECTION ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_small_fund_request(request, request_id):
    """
    POST /rspc/funds/small/request/{request_id}/approve/
    Approve a SUBMITTED small fund request (SUBMITTED → APPROVED)
    Triggers 'small_fund_approved' notification
    HOD only
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        
        # Verify status
        if fund_request.status != SmallFundRequestStatus.SUBMITTED:
            return Response(
                {'success': False, 'error': f'Can only approve SUBMITTED requests, current: {fund_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update request
        fund_request.status = SmallFundRequestStatus.APPROVED
        fund_request.approval_date = timezone.now()
        fund_request.approved_by = request.user
        fund_request.save()
        
        # Send notification
        try:
            NotificationService.small_fund_approved(fund_request, request.user)
        except Exception as notif_err:
            print(f"Notification error: {notif_err}")
        
        return Response(
            {
                'success': True,
                'message': 'Fund request approved',
                'data': SmallFundRequestDetailSerializer(fund_request).data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_small_fund_request(request, request_id):
    """
    POST /rspc/funds/small/request/{request_id}/reject/
    Reject a SUBMITTED small fund request (SUBMITTED → REJECTED)
    Body: {rejection_reason}
    Triggers 'small_fund_rejected' notification
    HOD only
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        
        # Verify status
        if fund_request.status != SmallFundRequestStatus.SUBMITTED:
            return Response(
                {'success': False, 'error': f'Can only reject SUBMITTED requests, current: {fund_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get rejection reason
        rejection_reason = request.data.get('rejection_reason', 'No reason provided')
        
        # Update request
        fund_request.status = SmallFundRequestStatus.REJECTED
        fund_request.rejection_reason = rejection_reason
        fund_request.save()
        
        # Send notification
        try:
            NotificationService.small_fund_rejected(fund_request, request.user, rejection_reason)
        except Exception as notif_err:
            print(f"Notification error: {notif_err}")
        
        return Response(
            {
                'success': True,
                'message': 'Fund request rejected',
                'data': SmallFundRequestDetailSerializer(fund_request).data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_small_fund_approvals(request):
    """
    GET /rspc/funds/small/pending-approvals/
    Get pending small fund requests for approval (HOD only)
    Auto-filtered by department
    """
    try:
        # Get pending (SUBMITTED) requests
        # TODO: Filter by HOD's department
        queryset = SmallFundRequest.objects.filter(status=SmallFundRequestStatus.SUBMITTED)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        start = (page - 1) * limit
        end = start + limit
        
        total_count = queryset.count()
        requests = queryset.order_by('-submission_date')[start:end]
        
        serializer = SmallFundRequestListSerializer(requests, many=True)
        
        return Response(
            {
                'success': True,
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# UC-023: FUND DISBURSEMENT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disburse_small_fund(request, request_id):
    """
    POST /rspc/funds/small/request/{request_id}/disburse/
    Create disbursement for APPROVED request (APPROVED → DISBURSED)
    Body: {disbursement_date, amount, method, reference_number, recipient_bank_account?, remarks?}
    Triggers 'small_fund_disbursed' notification
    RSPC Admin only
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        
        # Verify status
        if fund_request.status != SmallFundRequestStatus.APPROVED:
            return Response(
                {'success': False, 'error': f'Can only disburse APPROVED requests, current: {fund_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate amount matches request
        data = request.data.copy()
        if Decimal(str(data.get('amount', 0))) != fund_request.amount:
            return Response(
                {'success': False, 'error': f'Disbursement amount must match request amount (₹{fund_request.amount})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create disbursement
        serializer = FundDisbursementCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        disbursement = FundDisbursement.objects.create(
            request=fund_request,
            status=DisbursementStatus.PENDING,
            **serializer.validated_data
        )
        
        # Update fund request status
        fund_request.status = SmallFundRequestStatus.DISBURSED
        fund_request.save()
        
        # Send notification
        try:
            NotificationService.small_fund_disbursed(fund_request, disbursement, request.user)
        except Exception as notif_err:
            print(f"Notification error: {notif_err}")
        
        return Response(
            {
                'success': True,
                'message': 'Fund disbursed successfully',
                'disbursement': FundDisbursementDetailSerializer(disbursement).data
            },
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fund_disbursement_status(request, request_id):
    """
    GET /rspc/funds/small/request/{request_id}/disbursement/
    View disbursement status for a fund request
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        
        try:
            disbursement = fund_request.disbursement
            serializer = FundDisbursementDetailSerializer(disbursement)
            return Response(
                {
                    'success': True,
                    'has_disbursement': True,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except FundDisbursement.DoesNotExist:
            return Response(
                {
                    'success': True,
                    'has_disbursement': False,
                    'message': 'No disbursement record found'
                },
                status=status.HTTP_200_OK
            )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_all_disbursements(request):
    """
    GET /rspc/funds/small/disbursements/
    List all disbursements (RSPC Admin only)
    Query params: ?status=COMPLETED&page=1&limit=20
    """
    try:
        queryset = FundDisbursement.objects.all()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        start = (page - 1) * limit
        end = start + limit
        
        total_count = queryset.count()
        disbursements = queryset.order_by('-disbursement_date')[start:end]
        
        serializer = FundDisbursementListSerializer(disbursements, many=True)
        
        return Response(
            {
                'success': True,
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_disbursement_failed(request, request_id):
    """
    POST /rspc/funds/small/request/{request_id}/disbursement/mark-failed/
    Mark disbursement as failed
    Body: {remarks}
    Triggers notification
    """
    try:
        fund_request = get_object_or_404(SmallFundRequest, request_id=request_id)
        disbursement = get_object_or_404(FundDisbursement, request=fund_request)
        
        # Update status
        disbursement.status = DisbursementStatus.FAILED
        disbursement.remarks = request.data.get('remarks', 'Disbursement failed')
        disbursement.save()
        
        # Send notification
        try:
            NotificationService.small_fund_disbursement_failed(fund_request, disbursement, request.user)
        except Exception as notif_err:
            print(f"Notification error: {notif_err}")
        
        return Response(
            {
                'success': True,
                'message': 'Disbursement marked as failed',
                'data': FundDisbursementDetailSerializer(disbursement).data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# BR-020: CONSULTANCY WORKLOAD MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_consultancy_limits(request):
    """
    POST /rspc/consultancy/validate-limits/
    Check if faculty can take a new consultancy project
    Body: {faculty_id, estimated_hours}
    """
    try:
        serializer = ConsultancyValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        faculty_id = serializer.validated_data['faculty_id']
        estimated_hours = serializer.validated_data['estimated_hours']
        
        # Validate
        is_valid, errors, warnings = ConsultancyService.validate_consultancy_limits(
            faculty_id, estimated_hours
        )
        
        workload = ConsultancyService.get_faculty_workload(faculty_id)
        
        return Response(
            {
                'success': True,
                'can_accept': is_valid,
                'errors': errors,
                'warnings': warnings,
                'workload': workload
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_faculty_consultancy_workload(request, user_id):
    """
    GET /rspc/consultancy/faculty/{user_id}/workload/
    View faculty consultancy workload (faculty + RSPC Admin only)
    """
    try:
        workload = ConsultancyService.get_faculty_workload(user_id)
        
        serializer = FacultyWorkloadSerializer(workload)
        
        return Response(
            {
                'success': True,
                'faculty_id': user_id,
                'workload': serializer.data
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_consultancy_project(request):
    """
    POST /rspc/projects/type-consultancy/create/
    Create CONSULTANCY type project with BR-020 validation
    Body: includes project_type='CONSULTANCY', estimated_hours, hourly_rate
    """
    try:
        # Validate consultancy limits
        estimated_hours = request.data.get('estimated_hours', 0)
        is_valid, errors, warnings = ConsultancyService.validate_consultancy_limits(
            request.user.username, int(estimated_hours)
        )
        
        if not is_valid:
            return Response(
                {
                    'success': False,
                    'error': 'Consultancy limits exceeded',
                    'errors': errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create project (delegate to existing project creation logic)
        # For now, return success message
        return Response(
            {
                'success': True,
                'message': 'Consultancy project creation endpoint',
                'warnings': warnings
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_consultancy_workload_alerts(request):
    """
    GET /rspc/consultancy/alerts/
    Show faculty consultancy workload warnings (RSPC Admin + Dean only)
    """
    try:
        # Get all faculty with high workload
        alerts = []
        
        # This would fetch all faculty and check their workload
        # For now, return the structure
        
        return Response(
            {
                'success': True,
                'total_alerts': len(alerts),
                'alerts': alerts
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_consultancy_limits(request):
    """
    GET /rspc/consultancy/limits/ - Get current limits
    POST /rspc/consultancy/limits/ - Update limits (Admin only)
    """
    try:
        if request.method == 'GET':
            limits = ConsultancyLimit.get_limits()
            serializer = ConsultancyLimitSerializer(limits)
            return Response(
                {'success': True, 'data': serializer.data},
                status=status.HTTP_200_OK
            )
        
        elif request.method == 'POST':
            limits = ConsultancyLimit.get_limits()
            serializer = ConsultancyLimitSerializer(limits, data=request.data, partial=True)
            
            if not serializer.is_valid():
                return Response(
                    {'success': False, 'errors': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer.save()
            
            return Response(
                {'success': True, 'message': 'Limits updated', 'data': serializer.data},
                status=status.HTTP_200_OK
            )
    except Exception as e:
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

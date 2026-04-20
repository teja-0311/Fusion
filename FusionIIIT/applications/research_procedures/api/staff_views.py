"""
RSPC Staff Management API Views (UC-007, UC-008, UC-026, UC-027)
RESTful endpoints for staff request workflow with 7 approval stages
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from applications.research_procedures.models import (
    Staff, Committee, CommitteeVerdict, CommitteeMember, Project,
    StaffApprovalStatus, CommitteeDecision, StaffAllocation
)
from applications.research_procedures.api.staff_serializers import (
    StaffListSerializer, StaffDetailSerializer, StaffCreateSerializer,
    CommitteeSerializer, CommitteeCreateSerializer,
    CommitteeVerdictSerializer, VerdictSubmitSerializer,
    SelectionReportSerializer, StaffWorkflowSerializer,
    CommitteeMemberSerializer
)
from applications.research_procedures.staff_services import (
    create_staff_request, create_staff_committee,
    submit_committee_verdict, transition_staff_status,
    hod_approve_staff, rspc_approve_staff,
    generate_selection_report, get_staff_workflow_status
)
from applications.research_procedures.role_filters import (
    get_user_role, filter_staff_by_role, can_manage_staff
)
from applications.research_procedures.notification_service import NotificationService
from applications.globals.models import ExtraInfo


# ============================================================================
# STAFF REQUEST VIEWSET
# ============================================================================

class StaffViewSet(viewsets.ModelViewSet):
    """
    ViewSet for staff request management (UC-007, UC-008, UC-026, UC-027)
    
    Workflow stages:
        1. DRAFT - PI creates request
        2. COMMITTEE_PENDING - Assign committee
        3. COMMITTEE_APPROVED - Committee recommendation
        4. HOD_PENDING - HOD review
        5. HOD_APPROVED - HOD approval
        6. RSPC_PENDING - RSPC Admin review
        7. APPOINTED - Final approval
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StaffCreateSerializer
        elif self.action == 'list':
            return StaffListSerializer
        return StaffDetailSerializer
    
    def get_queryset(self):
        """Filter staff based on user role and permissions"""
        user = self.request.user
        queryset = Staff.objects.all()
        
        # Apply role-based filtering
        role = get_user_role(user.username)
        queryset = filter_staff_by_role(queryset, user.username, role)
        
        # Apply query filters
        approval_status = self.request.query_params.get('approval_status')
        if approval_status:
            queryset = queryset.filter(approval_status=approval_status)
        
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(pid=project_id)
        
        return queryset.order_by('-created_date')
    
    # ========================================================================
    # POST /api/staff/request/ - UC-007: Create staff request
    # ========================================================================
    
    def create(self, request, *args, **kwargs):
        """UC-007: Create initial staff request (DRAFT stage)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        success, message, staff = create_staff_request(
            project_id=serializer.validated_data.get('project_id'),
            data=serializer.validated_data,
            user=request.user
        )
        
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Send notification to RSPC Admin
        try:
            NotificationService.notify_staff_committee_pending(staff, request.user, staff.get_type_display())
        except:
            pass  # Notification failure should not block main operation
        
        return Response(
            StaffDetailSerializer(staff).data,
            status=status.HTTP_201_CREATED
        )
    
    # ========================================================================
    # GET /api/staff/ - List staff with role filtering
    # ========================================================================
    
    def list(self, request, *args, **kwargs):
        """List staff requests based on user role and filters"""
        return super().list(request, *args, **kwargs)
    
    # ========================================================================
    # GET /api/staff/{id}/ - Get staff details
    # ========================================================================
    
    def retrieve(self, request, *args, **kwargs):
        """Get detailed staff request information including workflow status"""
        staff = self.get_object()
        serializer = self.get_serializer(staff)
        
        # Add workflow status
        workflow_status = get_staff_workflow_status(staff.sid)
        data = serializer.data
        data['workflow'] = workflow_status
        
        return Response(data)
    
    # ========================================================================
    # POST /api/staff/{id}/committee/create/ - UC-026: Create committee
    # ========================================================================
    
    @action(detail=True, methods=['post'], url_path='committee/create')
    def create_committee(self, request, pk=None):
        """
        UC-026: Create staff selection committee (BR-RSPC-12)
        
        Enforces:
            - Minimum 3 members (BR-RSPC-12)
            - All PI-eligible (Professor/Assoc/Asst Prof)
        
        Request body:
        {
            "member_ids": [1, 2, 3, ...],
            "deadline": "2024-12-31T23:59:59Z",
            "name": "Staff Selection Committee"
        }
        """
        serializer = CommitteeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        success, message, committee = create_staff_committee(
            staff_id=pk,
            member_ids=serializer.validated_data['member_ids'],
            deadline=serializer.validated_data['deadline'],
            committee_name=serializer.validated_data.get('name', 'Staff Selection Committee'),
            user=request.user
        )
        
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Notify committee members
        staff = Staff.objects.get(sid=pk)
        for member_id in serializer.validated_data['member_ids']:
            try:
                member = ExtraInfo.objects.get(id=member_id)
                NotificationService.notify_staff_committee_pending(staff, member.user, staff.get_type_display())
            except:
                pass
        
        return Response(
            CommitteeSerializer(committee).data,
            status=status.HTTP_201_CREATED
        )
    
    # ========================================================================
    # POST /api/staff/{id}/verdict/ - UC-008: Submit committee verdict
    # ========================================================================
    
    @action(detail=True, methods=['post'], url_path='verdict')
    def submit_verdict(self, request, pk=None):
        """
        UC-008: Submit committee member verdict (BR-RSPC-15: Conflict of interest)
        
        Request body:
        {
            "member_id": 123,
            "decision": "APPROVE|REJECT|ABSTAIN",
            "comments": "Comments",
            "has_conflict_of_interest": false,
            "conflict_reason": ""
        }
        """
        serializer = VerdictSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        member_id = request.data.get('member_id')
        if not member_id:
            return Response(
                {'error': 'member_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = submit_committee_verdict(
            staff_id=pk,
            committee_member_id=member_id,
            decision=serializer.validated_data.get('decision'),
            comments=serializer.validated_data.get('comments', ''),
            has_conflict=serializer.validated_data.get('has_conflict_of_interest', False),
            conflict_reason=serializer.validated_data.get('conflict_reason', ''),
            user=request.user
        )
        
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        staff = Staff.objects.get(sid=pk)
        return Response(
            {
                'message': message,
                'staff': StaffDetailSerializer(staff).data
            },
            status=status.HTTP_200_OK
        )
    
    # ========================================================================
    # POST /api/staff/{id}/hod-approve/ - HOD approval
    # ========================================================================
    
    @action(detail=True, methods=['post'], url_path='hod-approve')
    def hod_approve(self, request, pk=None):
        """
        HOD approval/rejection (HOD_PENDING → HOD_APPROVED/HOD_REJECTED)
        
        Request body:
        {
            "action": "APPROVE|REJECT",
            "comments": "Comments"
        }
        """
        action_type = request.data.get('action', '').upper()
        if action_type not in ['APPROVE', 'REJECT']:
            return Response(
                {'error': 'action must be APPROVE or REJECT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = hod_approve_staff(
            staff_id=pk,
            action=action_type,
            comments=request.data.get('comments', ''),
            user=request.user
        )
        
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        staff = Staff.objects.get(sid=pk)
        
        # Notify RSPC Admin if approved
        if action_type == 'APPROVE':
            try:
                NotificationService.notify_staff_rspc_pending(staff, request.user, staff.get_type_display())
            except:
                pass
        
        return Response(
            {
                'message': message,
                'staff': StaffDetailSerializer(staff).data
            },
            status=status.HTTP_200_OK
        )
    
    # ========================================================================
    # POST /api/staff/{id}/rspc-approve/ - RSPC Admin final approval
    # ========================================================================
    
    @action(detail=True, methods=['post'], url_path='rspc-approve')
    def rspc_approve(self, request, pk=None):
        """
        RSPC Admin final approval (RSPC_PENDING → APPOINTED/RSPC_REJECTED)
        Creates StaffAllocation on appointment
        
        Request body:
        {
            "action": "APPROVE|REJECT",
            "comments": "Comments"
        }
        """
        action_type = request.data.get('action', '').upper()
        if action_type not in ['APPROVE', 'REJECT']:
            return Response(
                {'error': 'action must be APPROVE or REJECT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = rspc_approve_staff(
            staff_id=pk,
            action=action_type,
            comments=request.data.get('comments', ''),
            user=request.user
        )
        
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        staff = Staff.objects.get(sid=pk)
        
        # Notify PI if appointed
        if action_type == 'APPROVE':
            try:
                pi_user = staff.created_by or staff.pid.pi
                NotificationService.notify_staff_appointed(staff, pi_user, staff.person, staff.get_type_display())
            except:
                pass
        
        return Response(
            {
                'message': message,
                'staff': StaffDetailSerializer(staff).data
            },
            status=status.HTTP_200_OK
        )
    
    # ========================================================================
    # POST /api/staff/{id}/selection-report/ - UC-027: Selection report
    # ========================================================================
    
    @action(detail=True, methods=['post'], url_path='selection-report')
    def selection_report(self, request, pk=None):
        """
        UC-027: Submit final selection report
        
        Request body:
        {
            "selected_candidates": [
                {
                    "name": "Name",
                    "designation": "SRF",
                    "offer_date": "2024-01-01",
                    "stipend": 20000
                }
            ]
        }
        """
        serializer = SelectionReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        success, message = generate_selection_report(
            staff_id=pk,
            selected_candidates=serializer.validated_data['selected_candidates'],
            user=request.user
        )
        
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        staff = Staff.objects.get(sid=pk)
        
        # Notify HOD
        try:
            NotificationService.notify_staff_hod_pending(staff, request.user, staff.get_type_display())
        except:
            pass
        
        return Response(
            {
                'message': message,
                'staff': StaffDetailSerializer(staff).data
            },
            status=status.HTTP_200_OK
        )
    
    # ========================================================================
    # GET /api/staff/{id}/workflow/ - Workflow status
    # ========================================================================
    
    @action(detail=True, methods=['get'], url_path='workflow')
    def workflow_status(self, request, pk=None):
        """Get current workflow status and next steps"""
        status_data = get_staff_workflow_status(pk)
        
        if 'error' in status_data:
            return Response(status_data, status=status.HTTP_404_NOT_FOUND)
        
        return Response(status_data, status=status.HTTP_200_OK)


# ============================================================================
# COMMITTEE VIEWSET
# ============================================================================

class CommitteeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for committee management"""
    
    queryset = Committee.objects.all()
    serializer_class = CommitteeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter committees based on user role"""
        user = self.request.user
        queryset = Committee.objects.all()
        
        # Committee members see only their committees
        try:
            extra_info = ExtraInfo.objects.get(user=user)
            queryset = queryset.filter(members=extra_info)
        except ExtraInfo.DoesNotExist:
            queryset = queryset.none()
        
        return queryset.order_by('-created_at')


# ============================================================================
# COMMITTEE VERDICT VIEWSET
# ============================================================================

class CommitteeVerdictViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for committee verdicts"""
    
    queryset = CommitteeVerdict.objects.all()
    serializer_class = CommitteeVerdictSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter verdicts based on user role"""
        user = self.request.user
        
        try:
            extra_info = ExtraInfo.objects.get(user=user)
            return CommitteeVerdict.objects.filter(member=extra_info).order_by('-timestamp')
        except ExtraInfo.DoesNotExist:
            return CommitteeVerdict.objects.none()

"""
RSPC Expenditure Approval API Views
UC-012, UC-013, BR-RSPC-13 Implementation

6 Critical Endpoints:
1. POST /rspc/api/expenditures/ - Create expenditure request (UC-012)
2. GET /rspc/api/expenditures/ - List expenditures (UC-013) with role filtering
3. GET /rspc/api/expenditures/{id}/ - Details with approval history
4. POST /rspc/api/expenditures/{id}/approve/ - Approve at current level
5. POST /rspc/api/expenditures/{id}/reject/ - Reject at any level
6. GET /rspc/api/expenditures/{id}/history/ - Approval history
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q

from ..models import Expenditure, ExpenditureApprovalHistory, Project, ExtraInfo, ExpenditureStatus, CurrentApprover
from .expenditure_serializers import (
    ExpenditureCreateSerializer, ExpenditureListSerializer,
    ExpenditureDetailSerializer, ExpenditureApproveSerializer,
    ExpenditureRejectSerializer, ExpenditureApprovalHistorySerializer
)
from ..expenditure_services import (
    ExpenditureApprovalService, ExpenditureValidationService,
    ExpenditureRoutingService, ExpenditureQueryService
)


class ExpenditureListPagination(PageNumberPagination):
    """Pagination for expenditure lists"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ExpenditureViewSet(viewsets.ModelViewSet):
    """
    Expenditure Approval System ViewSet (UC-012, UC-013, BR-RSPC-13)
    
    Critical Business Rules:
    - 3-tier approval based on amount (BR-RSPC-13)
    - Role-based access control
    - Cannot approve own expenditure
    - Automatic routing to next approver
    """
    
    queryset = Expenditure.objects.all()
    serializer_class = ExpenditureDetailSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ExpenditureListPagination
    http_method_names = ['get', 'post', 'head', 'options']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ExpenditureCreateSerializer
        elif self.action == 'list':
            return ExpenditureListSerializer
        elif self.action == 'approve':
            return ExpenditureApproveSerializer
        elif self.action == 'reject':
            return ExpenditureRejectSerializer
        return ExpenditureDetailSerializer
    
    def get_queryset(self):
        """Filter expenditures based on user role (UC-013)"""
        user = self.request.user
        role = ExpenditureQueryService.get_user_role(user)
        
        return ExpenditureQueryService.get_filtered_expenditures(user, role)
    
    def create(self, request, *args, **kwargs):
        """
        UC-012: Create expenditure request with validation and auto-routing
        
        Validates:
        - Amount positive
        - Category valid
        - Purpose ≥ 20 chars
        - Budget sufficient
        - Supporting docs if > ₹50K
        
        Auto-routes based on amount (BR-RSPC-13):
        - ≤₹50K → PI only
        - ₹50K-₹200K → PI then HOD
        - >₹200K → PI then HOD then RSPC Admin
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Get project
            project_id = serializer.validated_data['project_id']
            project = get_object_or_404(Project, pid=project_id)
            
            # Get requested_by user
            try:
                requested_by = ExtraInfo.objects.get(user=request.user)
            except ExtraInfo.DoesNotExist:
                return Response(
                    {'error': 'User profile not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create expenditure with automatic routing
            success, result = ExpenditureApprovalService.create_expenditure(
                project=project,
                amount=serializer.validated_data['amount'],
                category=serializer.validated_data['category'],
                purpose=serializer.validated_data['purpose'],
                requested_by=requested_by,
                supporting_docs=serializer.validated_data.get('supporting_documents', [])
            )
            
            if not success:
                return Response(
                    {'error': result},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Return created expenditure details
            expenditure_serializer = ExpenditureDetailSerializer(result)
            return Response(
                expenditure_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def list(self, request, *args, **kwargs):
        """
        UC-013: List expenditures with role-based filtering
        
        Visibility:
        - PI: Own expenditures
        - HOD: Department expenditures
        - RSPC Admin: All expenditures
        
        Supports filtering by:
        - status
        - category
        - amount range
        - current_approver
        """
        queryset = self.get_queryset()
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        category_filter = request.query_params.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        approver_filter = request.query_params.get('current_approver')
        if approver_filter:
            queryset = queryset.filter(current_approver=approver_filter)
        
        amount_min = request.query_params.get('amount_min')
        if amount_min:
            queryset = queryset.filter(amount__gte=amount_min)
        
        amount_max = request.query_params.get('amount_max')
        if amount_max:
            queryset = queryset.filter(amount__lte=amount_max)
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get detailed expenditure with full approval history"""
        expenditure = get_object_or_404(Expenditure, eid=pk)
        
        # Check access
        if not self._can_access_expenditure(request.user, expenditure):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(expenditure)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        POST /rspc/api/expenditures/{id}/approve/
        
        Approve expenditure at current stage
        
        Business Rules:
        - Cannot approve own request (conflict of interest)
        - Must be current approver role
        - Role-based amount validation
        - Auto-route to next approver or mark APPROVED
        """
        expenditure = get_object_or_404(Expenditure, eid=pk)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get approver info
            try:
                approver = ExtraInfo.objects.get(user=request.user)
            except ExtraInfo.DoesNotExist:
                return Response(
                    {'error': 'User profile not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Approve
            success, message = ExpenditureApprovalService.approve_expenditure(
                expenditure=expenditure,
                approver=approver,
                approver_role=serializer.validated_data['approver_role'],
                comments=serializer.validated_data.get('comments', '')
            )
            
            if not success:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Return updated expenditure
            expenditure.refresh_from_db()
            expenditure_serializer = ExpenditureDetailSerializer(expenditure)
            return Response({
                'message': message,
                'expenditure': expenditure_serializer.data
            })
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        POST /rspc/api/expenditures/{id}/reject/
        
        Reject expenditure and send back to PI
        
        Business Rules:
        - Can reject at any stage
        - Sends back to PI with comments
        - Records rejection in history
        """
        expenditure = get_object_or_404(Expenditure, eid=pk)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get rejecter info
            try:
                rejecter = ExtraInfo.objects.get(user=request.user)
            except ExtraInfo.DoesNotExist:
                return Response(
                    {'error': 'User profile not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reject
            success, message = ExpenditureApprovalService.reject_expenditure(
                expenditure=expenditure,
                rejecter=rejecter,
                rejecter_role=serializer.validated_data['rejecter_role'],
                reason=serializer.validated_data['reason']
            )
            
            if not success:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Return updated expenditure
            expenditure.refresh_from_db()
            expenditure_serializer = ExpenditureDetailSerializer(expenditure)
            return Response({
                'message': message,
                'expenditure': expenditure_serializer.data
            })
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        GET /rspc/api/expenditures/{id}/history/
        
        Get complete approval history with all stages and actions
        """
        expenditure = get_object_or_404(Expenditure, eid=pk)
        
        # Check access
        if not self._can_access_expenditure(request.user, expenditure):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        history = expenditure.approval_history.all()
        serializer = ExpenditureApprovalHistorySerializer(history, many=True)
        
        return Response({
            'expenditure_id': expenditure.eid,
            'approval_chain': expenditure.approval_chain,
            'history': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """
        Get expenditures pending this user's approval
        
        Filters by user's role automatically
        """
        user = request.user
        role = ExpenditureQueryService.get_user_role(user)
        
        pending = ExpenditureQueryService.get_approval_pending_for_user(user, role)
        
        page = self.paginate_queryset(pending)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    def _can_access_expenditure(self, user, expenditure):
        """Check if user can access this expenditure"""
        role = ExpenditureQueryService.get_user_role(user)
        
        if role == 'RSPC':
            return True
        
        if role == 'PI':
            # Can access if own expenditure or in own project
            try:
                extra_info = ExtraInfo.objects.get(user=user)
                pi_projects = Project.objects.filter(pi_id=extra_info.user.username)
                return expenditure.project in pi_projects or expenditure.requested_by == extra_info
            except:
                return False
        
        if role == 'HOD':
            # Can access if in same department
            try:
                extra_info = ExtraInfo.objects.get(user=user)
                return expenditure.project.dept == extra_info.department
            except:
                return False
        
        return False

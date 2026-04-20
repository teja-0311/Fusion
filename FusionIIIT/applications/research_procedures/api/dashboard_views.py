"""
RSPC Dashboard API Endpoints
Part 2: Dashboard integration with real data
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import logging

from ..dashboard_services import DashboardService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """
    GET /rspc/api/dashboard/
    
    Returns role-specific dashboard data including:
    - pending_items: Count of items awaiting action
    - recent_projects: Last 5 projects
    - budget_summary: Total, utilized, remaining, alerts
    - quick_stats: Overview statistics
    - notifications: Unread count and recent notifications
    
    Response structure is role-dependent (PI, HOD, Dean, Director, Admin, Committee)
    """
    try:
        dashboard_data = DashboardService.get_dashboard(request)
        return Response(dashboard_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Dashboard error for user {request.user.username}: {str(e)}")
        return Response(
            {'error': 'Failed to generate dashboard data', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_approvals(request):
    """
    GET /rspc/api/dashboard/pending-approvals/
    
    Returns pending approvals by role:
    - pi_pending: Expenditures awaiting PI approval
    - hod_pending: Expenditures awaiting HOD approval
    - dean_pending: Expenditures awaiting Dean approval
    """
    try:
        from .models import Expenditure
        from .role_filters import get_user_roles, get_faculty_by_username, get_user_department
        
        username = request.user.username
        roles = get_user_roles(username)
        faculty = get_faculty_by_username(username)
        department_id = get_user_department(username)
        
        result = {}
        
        # PI pending
        if roles['pi'] and faculty:
            from django.db.models import Q
            result['pi_pending'] = Expenditure.objects.filter(
                project__pi_id=faculty.id,
                status='pending_pi'
            ).count()
        
        # HOD pending
        if roles['hod'] and department_id:
            from django.db.models import Q
            result['hod_pending'] = Expenditure.objects.filter(
                Q(project__dept=str(department_id)),
                status='pending_hod'
            ).count()
        
        # Dean/Admin pending
        if roles['dean_rspc'] or roles['rspc_admin']:
            result['dean_pending'] = Expenditure.objects.filter(
                status__in=['pending_dean', 'pending_admin']
            ).count()
        
        result['total'] = sum(result.values())
        
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Pending approvals error: {str(e)}")
        return Response(
            {'error': 'Failed to fetch pending approvals'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

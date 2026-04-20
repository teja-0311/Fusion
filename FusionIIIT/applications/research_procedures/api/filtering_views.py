"""
RSPC Role-Based Filtering Integration Middleware
Part 3: Apply filter_* functions to list endpoints
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import logging

from ..models import Project, Budget, Staff, Expenditure, Request
from ..role_filters import (
    filter_projects_by_role, filter_expenditures_by_role,
    filter_staff_by_role, filter_budget_by_role,
    filter_requests_by_role, get_user_roles, get_faculty_by_username
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def projects_list(request):
    """
    GET /rspc/api/projects/
    
    Returns role-filtered projects list
    - PI: only own projects (as PI or Co-PI)
    - HOD: department projects
    - Dean/Admin: all projects
    - Director: all (summary only)
    """
    try:
        role = request.query_params.get('role')
        if not role:
            # Determine primary role
            roles = get_user_roles(request.user.username)
            if roles['pi']:
                role = 'pi'
            elif roles['hod']:
                role = 'hod'
            elif roles['dean_rspc']:
                role = 'dean_rspc'
            elif roles['director']:
                role = 'director'
            elif roles['rspc_admin']:
                role = 'rspc_admin'
            else:
                return Response({'error': 'No valid role'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all projects and apply filter
        projects_qs = Project.objects.all()
        filtered = filter_projects_by_role(projects_qs, request.user.username, role)
        
        # Serialize
        from .serializers import ProjectSerializer
        serializer = ProjectSerializer(filtered, many=True)
        
        return Response({
            'count': len(filtered),
            'role': role,
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Projects list error: {str(e)}")
        return Response(
            {'error': 'Failed to fetch projects', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expenditures_list(request):
    """
    GET /rspc/api/expenditures/
    
    Returns role-filtered expenditures
    - PI: own project expenditures
    - HOD: 50-200K range in department
    - Dean: > 200K only
    - Admin: all
    """
    try:
        role = request.query_params.get('role')
        if not role:
            roles = get_user_roles(request.user.username)
            if roles['pi']:
                role = 'pi'
            elif roles['hod']:
                role = 'hod'
            elif roles['dean_rspc']:
                role = 'dean_rspc'
            elif roles['director']:
                role = 'director'
            elif roles['rspc_admin']:
                role = 'rspc_admin'
            else:
                return Response({'error': 'No valid role'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all expenditures and apply filter
        expenditures_qs = Expenditure.objects.all()
        filtered = filter_expenditures_by_role(expenditures_qs, request.user.username, role)
        
        # Return simplified response
        return Response({
            'count': filtered.count(),
            'role': role,
            'results': [
                {
                    'id': e.id,
                    'amount': float(e.amount) if hasattr(e, 'amount') else 0,
                    'status': getattr(e, 'status', 'unknown'),
                } for e in filtered
            ]
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Expenditures list error: {str(e)}")
        return Response(
            {'error': 'Failed to fetch expenditures', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_list(request):
    """
    GET /rspc/api/staff/
    
    Returns role-filtered staff positions
    - PI: own project staff
    - HOD: department staff
    - Dean/Admin: all staff
    - Committee: own assignments
    """
    try:
        role = request.query_params.get('role')
        if not role:
            roles = get_user_roles(request.user.username)
            if roles['pi']:
                role = 'pi'
            elif roles['hod']:
                role = 'hod'
            elif roles['dean_rspc']:
                role = 'dean_rspc'
            elif roles['committee']:
                role = 'committee'
            elif roles['rspc_admin']:
                role = 'rspc_admin'
            else:
                return Response({'error': 'No valid role'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all staff and apply filter
        staff_qs = Staff.objects.all()
        filtered = filter_staff_by_role(staff_qs, request.user.username, role)
        
        # Return simplified response
        return Response({
            'count': filtered.count(),
            'role': role,
            'results': [
                {
                    'id': s.id,
                    'status': getattr(s, 'status', 'unknown'),
                } for s in filtered
            ]
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Staff list error: {str(e)}")
        return Response(
            {'error': 'Failed to fetch staff', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budget_list(request):
    """
    GET /rspc/api/budgets/
    
    Returns role-filtered budgets
    - PI: own project budgets
    - HOD: department budgets
    - Dean/Admin: all budgets
    """
    try:
        role = request.query_params.get('role')
        if not role:
            roles = get_user_roles(request.user.username)
            if roles['pi']:
                role = 'pi'
            elif roles['hod']:
                role = 'hod'
            elif roles['dean_rspc']:
                role = 'dean_rspc'
            elif roles['director']:
                role = 'director'
            elif roles['rspc_admin']:
                role = 'rspc_admin'
            else:
                return Response({'error': 'No valid role'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all budgets and apply filter
        budget_qs = Budget.objects.all()
        filtered = filter_budget_by_role(budget_qs, request.user.username, role)
        
        # Return simplified response
        return Response({
            'count': filtered.count(),
            'role': role,
            'results': [
                {
                    'id': b.bid,
                    'project': b.project.name if b.project else 'Unknown',
                    'total_sanctioned': float(b.total_sanctioned) if b.total_sanctioned else 0,
                } for b in filtered
            ]
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Budget list error: {str(e)}")
        return Response(
            {'error': 'Failed to fetch budgets', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def requests_list(request):
    """
    GET /rspc/api/requests/
    
    Returns role-filtered requests (funds, staff)
    - PI: own requests
    - HOD: department requests
    - Dean: all (for final approval)
    - Director: fund requests only
    - Admin: all
    """
    try:
        role = request.query_params.get('role')
        if not role:
            roles = get_user_roles(request.user.username)
            if roles['pi']:
                role = 'pi'
            elif roles['hod']:
                role = 'hod'
            elif roles['dean_rspc']:
                role = 'dean_rspc'
            elif roles['director']:
                role = 'director'
            elif roles['rspc_admin']:
                role = 'rspc_admin'
            else:
                return Response({'error': 'No valid role'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all requests and apply filter
        requests_qs = Request.objects.all()
        filtered = filter_requests_by_role(requests_qs, request.user.username, role)
        
        # Return simplified response
        return Response({
            'count': filtered.count(),
            'role': role,
            'results': [
                {
                    'id': r.id,
                    'request_type': getattr(r, 'request_type', 'unknown'),
                    'status': getattr(r, 'status', 'unknown'),
                } for r in filtered
            ]
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Requests list error: {str(e)}")
        return Response(
            {'error': 'Failed to fetch requests', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

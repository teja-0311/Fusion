"""
RSPC Module - Project Management Views
UC-004, UC-005, UC-012, UC-013 implementations

API Endpoints:
- UC-004: PATCH /rspc/projects/{project_id}/ - Update project
- UC-004: GET /rspc/projects/{project_id}/versions/ - List project versions
- UC-004: GET /rspc/projects/{project_id}/versions/{version_id}/ - Get specific version
- UC-005: POST /rspc/projects/{project_id}/cancel/ - Cancel project
- UC-005: GET /rspc/projects/{project_id}/cancellation-details/ - View cancellation
- UC-005: POST /rspc/projects/{project_id}/cancel-request/ - Request cancellation (optional)
- UC-012: POST /rspc/proposals/{project_id}/vet/ - HOD vet proposal
- UC-012: GET /rspc/proposals/{project_id}/vetting/ - View vetting details
- UC-012: GET /rspc/proposals/pending-vetting/ - List pending vetting
- UC-012: POST /rspc/proposals/{project_id}/vetting/revert/ - Revert vetting
- UC-013: GET /rspc/projects/department/ - HOD department projects
- UC-013: GET /rspc/projects/department/summary/ - HOD dashboard summary
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from ..models import Project, ProjectVersion, ProposalVetting
from ..project_services import (
    ProjectVersionService, ProjectCancellationService,
    ProposalVettingService, DepartmentProjectsService
)
from ..api.serializers import (
    ProjectUpdateSerializer, ProjectVersionSerializer, ProjectVersionDetailSerializer,
    ProjectCancellationSerializer, CancellationDetailsSerializer,
    ProposalVettingSerializer, ProposalVettingDetailSerializer, VettingRevertSerializer,
    DepartmentProjectsResponseSerializer, DepartmentSummarySerializer,
    PendingVettingProjectSerializer
)


# ============================================================================
# UC-004: PROJECT UPDATE ENDPOINTS
# ============================================================================

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_project(request, project_id):
    """
    PATCH /rspc/projects/{project_id}/
    
    Update project details (UC-004)
    BR-011: No updates after approval unless allow_updates_after_approval=True
    
    Request:
    {
        "name": "New title (optional)",
        "description": "New description (optional)",
        "total_budget": 500000,
        "change_reason": "Budget increased for equipment",
        "change_type": "BUDGET"
    }
    
    Response (200):
    {
        "success": true,
        "project": {...},
        "version": {...},
        "message": "Project updated to version 2"
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    # Check authorization - only PI can update
    if project.pi_id != request.user.username:
        return Response(
            {'success': False, 'error': 'Only PI can update this project'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProjectUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Prepare updates
    updates = {}
    for field in ['name', 'description', 'total_budget', 'allow_updates_after_approval']:
        if field in serializer.validated_data:
            updates[field] = serializer.validated_data[field]
    
    # Call service
    success, message, version = ProjectVersionService.update_project(
        project=project,
        user=request.user,
        updates=updates,
        change_reason=serializer.validated_data['change_reason'],
        change_type=serializer.validated_data['change_type']
    )
    
    if not success:
        return Response(
            {'success': False, 'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Refresh project
    project.refresh_from_db()
    
    return Response(
        {
            'success': True,
            'message': message,
            'project': {
                'pid': project.pid,
                'name': project.name,
                'description': project.description,
                'total_budget': str(project.total_budget),
                'last_updated_by': project.last_updated_by.get_full_name() if project.last_updated_by else None,
                'last_updated_date': project.last_updated_date
            },
            'version': {
                'version_number': version.version_number,
                'change_type': version.change_type,
                'change_reason': version.change_reason
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_project_versions(request, project_id):
    """
    GET /rspc/projects/{project_id}/versions/
    
    List all versions of a project (newest first)
    Role: PI + approvers
    
    Response (200):
    {
        "success": true,
        "total_versions": 3,
        "versions": [
            {"version_number": 2, "title": "...", ...},
            {"version_number": 1, "title": "...", ...}
        ]
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    # Check authorization
    is_pi = project.pi_id == request.user.username
    if not is_pi:
        return Response(
            {'success': False, 'error': 'Only PI can view versions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    versions = ProjectVersionService.get_project_versions(project, limit=50)
    
    return Response(
        {
            'success': True,
            'project_id': project.pid,
            'project_name': project.name,
            'total_versions': len(versions),
            'versions': versions
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_version(request, project_id, version_id):
    """
    GET /rspc/projects/{project_id}/versions/{version_id}/
    
    Get specific version details
    Show full snapshot of that version
    
    Response (200):
    {
        "success": true,
        "version": {...}
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    # Check authorization
    is_pi = project.pi_id == request.user.username
    if not is_pi:
        return Response(
            {'success': False, 'error': 'Only PI can view versions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    version_data = ProjectVersionService.get_version_details(project, version_id)
    if not version_data:
        return Response(
            {'success': False, 'error': 'Version not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response(
        {
            'success': True,
            'version': version_data
        },
        status=status.HTTP_200_OK
    )


# ============================================================================
# UC-005: PROJECT CANCELLATION ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_project(request, project_id):
    """
    POST /rspc/projects/{project_id}/cancel/
    
    Cancel a project (UC-005)
    
    Request:
    {
        "cancellation_reason": "Project scope changed"
    }
    
    Response (200):
    {
        "success": true,
        "message": "Project cancelled successfully"
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    serializer = ProjectCancellationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check authorization - PI or Admin
    success, message = ProjectCancellationService.cancel_project(
        project=project,
        user=request.user,
        cancellation_reason=serializer.validated_data['cancellation_reason']
    )
    
    if not success:
        return Response(
            {'success': False, 'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    project.refresh_from_db()
    
    return Response(
        {
            'success': True,
            'message': message,
            'project': {
                'pid': project.pid,
                'name': project.name,
                'status': project.status,
                'cancellation_reason': project.cancellation_reason,
                'cancelled_date': project.cancelled_date
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cancellation_details(request, project_id):
    """
    GET /rspc/projects/{project_id}/cancellation-details/
    
    View cancellation details
    Role: PI + RSPC Admin + Dean
    
    Response (200):
    {
        "success": true,
        "cancellation": {...}
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    details = ProjectCancellationService.get_cancellation_details(project)
    if not details:
        return Response(
            {'success': False, 'error': 'Project has not been cancelled'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response(
        {
            'success': True,
            'cancellation': details
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_project_cancellation(request, project_id):
    """
    POST /rspc/projects/{project_id}/cancel-request/
    
    PI requests project cancellation (optional workflow)
    RSPC Admin must approve
    
    Request:
    {
        "reason": "Project cannot continue"
    }
    
    Response (200):
    {
        "success": true,
        "request_id": 123,
        "status": "PENDING"
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    # Check authorization - PI only
    if project.pi_id != request.user.username:
        return Response(
            {'success': False, 'error': 'Only PI can request cancellation'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProjectCancellationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, request_id = ProjectCancellationService.create_cancellation_request(
        project=project,
        user=request.user,
        reason=serializer.validated_data['cancellation_reason']
    )
    
    if not success:
        return Response(
            {'success': False, 'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response(
        {
            'success': True,
            'message': message,
            'request_id': request_id,
            'status': 'PENDING'
        },
        status=status.HTTP_201_CREATED
    )


# ============================================================================
# UC-012: PROPOSAL VETTING ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vet_proposal(request, project_id):
    """
    POST /rspc/proposals/{project_id}/vet/
    
    HOD vetting proposal (UC-012)
    Permission: HOD of department only
    
    Request:
    {
        "technical_feasibility": "PASS",
        "academic_relevance": "PASS",
        "resource_adequacy": "FLAG",
        "department_alignment": "PASS",
        "comments": "Project looks good but resources need review"
    }
    
    Response (200):
    {
        "success": true,
        "vetting_id": 1,
        "status": "APPROVED",
        "next_step": "Director review"
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    serializer = ProposalVettingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, result = ProposalVettingService.vet_proposal(
        project=project,
        user=request.user,
        technical_feasibility=serializer.validated_data['technical_feasibility'],
        academic_relevance=serializer.validated_data['academic_relevance'],
        resource_adequacy=serializer.validated_data['resource_adequacy'],
        department_alignment=serializer.validated_data['department_alignment'],
        comments=serializer.validated_data.get('comments', '')
    )
    
    if not success:
        return Response(
            {'success': False, 'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response(
        {
            'success': True,
            'message': message,
            'vetting': result
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_vetting_details(request, project_id):
    """
    GET /rspc/proposals/{project_id}/vetting/
    
    View vetting details (if completed)
    Role: PI, HOD, Dean RSPC, RSPC Admin
    
    Response (200):
    {
        "success": true,
        "vetting": {...}
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    details = ProposalVettingService.get_vetting_details(project)
    if not details:
        return Response(
            {'success': False, 'error': 'Vetting not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response(
        {
            'success': True,
            'vetting': details
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_vetting(request):
    """
    GET /rspc/proposals/pending-vetting/
    
    List projects pending HOD vetting
    Filtered by logged-in user's department (HOD role)
    Role: HOD only
    Pagination
    
    Response (200):
    {
        "success": true,
        "pending_count": 3,
        "projects": [...]
    }
    """
    projects, total = DepartmentProjectsService.get_pending_vetting(request.user)
    
    if not projects:
        return Response(
            {
                'success': True,
                'pending_count': 0,
                'projects': []
            },
            status=status.HTTP_200_OK
        )
    
    return Response(
        {
            'success': True,
            'pending_count': total,
            'projects': projects
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revert_vetting(request, project_id):
    """
    POST /rspc/proposals/{project_id}/vetting/revert/
    
    HOD reverts vetting to change decision
    Only if not yet moved to Director
    
    Request:
    {
        "reason": "Need to reconsider resource allocation"
    }
    
    Response (200):
    {
        "success": true,
        "message": "Vetting reverted"
    }
    """
    project = get_object_or_404(Project, pid=project_id)
    
    serializer = VettingRevertSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = ProposalVettingService.revert_vetting(
        project=project,
        user=request.user,
        reason=serializer.validated_data['reason']
    )
    
    if not success:
        return Response(
            {'success': False, 'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response(
        {
            'success': True,
            'message': message
        },
        status=status.HTTP_200_OK
    )


# ============================================================================
# UC-013: DEPARTMENT PROJECTS ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_projects(request):
    """
    GET /rspc/projects/department/
    
    HOD views all projects in their department
    Auto-filter by HOD's department
    
    Query params:
    - status: filter by status
    - vetting_status: filter by vetting status
    - limit: page size (default 20)
    - offset: pagination offset
    
    Response (200):
    {
        "success": true,
        "total_projects": 10,
        "projects": [...],
        "vetting_pending_count": 2,
        "approved_count": 5,
        "rejected_count": 1
    }
    """
    status_filter = request.query_params.get('status')
    vetting_status_filter = request.query_params.get('vetting_status')
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    projects, total = DepartmentProjectsService.get_hod_projects(
        user=request.user,
        status_filter=status_filter,
        vetting_status_filter=vetting_status_filter,
        limit=limit,
        offset=offset
    )
    
    # Get counts
    summary = DepartmentProjectsService.get_hod_summary(request.user)
    
    return Response(
        {
            'success': True,
            'total_projects': total,
            'projects': projects,
            'vetting_pending_count': summary.get('vetting_pending', 0),
            'approved_count': summary.get('vetted', 0),
            'rejected_count': summary.get('rejected', 0)
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_summary(request):
    """
    GET /rspc/projects/department/summary/
    
    HOD sees dashboard summary
    Totals: submitted, vetted, approved, rejected
    Budget totals
    
    Response (200):
    {
        "success": true,
        "summary": {
            "submitted": 10,
            "vetted": 5,
            "approved": 4,
            "rejected": 1,
            ...
        }
    }
    """
    summary = DepartmentProjectsService.get_hod_summary(request.user)
    
    if 'error' in summary:
        return Response(
            {'success': False, 'error': summary['error']},
            status=status.HTTP_403_FORBIDDEN
        )
    
    return Response(
        {
            'success': True,
            'summary': summary
        },
        status=status.HTTP_200_OK
    )

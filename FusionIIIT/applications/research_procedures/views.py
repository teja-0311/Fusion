"""
RSPC Module - API Views (Thin Boundaries)
All endpoints delegate to services and handle HTTP concerns only
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
import json
from decimal import Decimal
from typing import Dict

from . import services
from . import selectors
from . import budget_services
from .role_filters import get_user_roles
from .api.serializers import *
from .models import Budget, BudgetReallocation, BudgetModificationHistory, Project
from applications.globals.models import ExtraInfo, HoldsDesignation

# Import gap items views
from .api.gap_items_views import (
    create_small_fund_request, update_small_fund_request, submit_small_fund_request,
    list_small_fund_requests, get_small_fund_request_details,
    approve_small_fund_request, reject_small_fund_request, get_pending_small_fund_approvals,
    disburse_small_fund, get_fund_disbursement_status, list_all_disbursements, mark_disbursement_failed,
    validate_consultancy_limits, get_faculty_consultancy_workload, create_consultancy_project,
    get_consultancy_workload_alerts, manage_consultancy_limits
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_info(request):
    """Extract user info from request"""
    return {
        'username': request.user.username,
        'name': request.user.get_full_name(),
    }


def _get_primary_role(username: str) -> str:
    """Resolve primary RSPC role for UI workflow decisions."""
    roles = get_user_roles(username)
    if roles.get('rspc_admin'):
        return 'rspc_admin'
    if roles.get('dean_rspc'):
        return 'dean_rspc'
    if roles.get('hod'):
        return 'hod'
    if roles.get('pi'):
        return 'pi'
    if roles.get('committee'):
        return 'committee'
    if roles.get('director'):
        return 'director'
    return 'guest'


def _project_actions_for_user(project_obj: Project, username: str) -> Dict:
    """
    Compute role-specific project actions for client-side workflow rendering.
    This keeps Dean/HOD/Director/Admin/PI operations distinct on the same page.
    """
    roles = get_user_roles(username)
    is_owner_pi = selectors.user_matches_project_pi(username, project_obj.pi_id)
    in_user_dept = selectors.user_department_matches_project(username, project_obj.dept)
    status = project_obj.status
    hod_vetting = getattr(project_obj, 'hod_vetting_status', 'PENDING')

    can_vet_proposal = roles.get('hod', False) and in_user_dept and status in ['PROPOSED', 'SUBMITTED'] and hod_vetting == 'PENDING'
    can_verify_proposal = (roles.get('rspc_admin', False) or roles.get('dean_rspc', False)) and status in ['PROPOSED', 'SUBMITTED', 'UNDER_REVIEW']
    can_dean_decide = roles.get('dean_rspc', False) and status in ['UNDER_REVIEW', 'PROPOSED'] and hod_vetting in ['APPROVED', 'PENDING']

    return {
        'role': _get_primary_role(username),
        'can_view': True,
        'can_edit': bool(is_owner_pi and status in ['PROPOSED', 'REJECTED']) or roles.get('rspc_admin', False),
        'can_cancel': bool(is_owner_pi and status not in ['COMPLETED', 'CANCELLED']) or roles.get('rspc_admin', False),
        'can_register': roles.get('rspc_admin', False) and status == 'SANCTIONED',
        'can_commence': roles.get('rspc_admin', False) and status == 'SANCTIONED',
        'can_close': (is_owner_pi or roles.get('rspc_admin', False)) and status in ['ONGOING', 'EXTENDED'],
        'can_vet_proposal': can_vet_proposal,
        'can_verify_proposal': can_verify_proposal,
        'can_dean_approve_reject': can_dean_decide,
        'can_view_department_summary': roles.get('hod', False),
        'can_view_institute_summary': roles.get('dean_rspc', False) or roles.get('director', False) or roles.get('rspc_admin', False),
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def rspc_login_api(request):
    """
    POST /rspc/api/rspc-login/
    RSPC Module API Login - Supports all 6 roles
    
    Request JSON:
    {
        "username": "username",
        "password": "password",
        "role": "pi"  # or "hod", "dean_rspc", "director", "rspc_admin", "committee"
    }
    
    Response on success (200):
    {
        "success": true,
        "role": "pi",
        "role_label": "Faculty/PI",
        "role_description": "Principal Investigator",
        "user": {
            "username": "username",
            "full_name": "Full Name",
            "department": "Department Name"
        }
    }
    
    Response on error (401/403):
    {
        "success": false,
        "error": "Invalid credentials" or "User does not have this role"
    }
    """
    if request.method != 'POST':
        return Response(
            {'success': False, 'error': 'Method not allowed'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    try:
        if isinstance(request.data, dict):
            data = request.data
        else:
            data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return Response(
            {'success': False, 'error': 'Invalid JSON'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    requested_role = data.get('role', '').lower()
    
    # Validate inputs
    if not username or not password:
        return Response(
            {'success': False, 'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not requested_role:
        return Response(
            {'success': False, 'error': 'Role is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {'success': False, 'error': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Helper function to get user designations
    def get_user_designations(user):
        try:
            designations = HoldsDesignation.objects.filter(user=user).select_related('designation')
            return [hd.designation.name for hd in designations]
        except:
            return []
    
    # Map role name to designation and validate user has the role
    role_mapping = {
        'pi': ['faculty_pi', 'Professor', 'Assoc. Prof', 'Asst. Prof'],
        'hod': ['hod'],
        'dean_rspc': ['dean_rspc'],
        'director': ['director'],
        'rspc_admin': ['rspc_admin'],
        'committee': ['committee'],
    }
    
    role_labels = {
        'pi': 'Faculty/PI',
        'hod': 'Head of Department',
        'dean_rspc': 'Dean (RSPC)',
        'director': 'Director',
        'rspc_admin': 'RSPC Administrator',
        'committee': 'Committee Member',
    }
    
    role_descriptions = {
        'pi': 'Principal Investigator - Can submit proposals, manage projects, request staff',
        'hod': 'Head of Department - Approves expenditures (₹50K-₹200K), manages department',
        'dean_rspc': 'Dean RSPC - Final approval authority for proposals, funds, and >₹200K expenditures',
        'director': 'Director - Strategic oversight, fund allocation authority',
        'rspc_admin': 'RSPC Administrator - Full system access, verification, and administration',
        'committee': 'Committee Member - Reviews and recommends staff selections',
    }
    
    # Check if role exists
    if requested_role not in role_mapping:
        return Response(
            {'success': False, 'error': f'Invalid role: {requested_role}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user has the requested role
    user_designations = get_user_designations(user)
    required_designations = role_mapping[requested_role]
    
    has_role = any(des in required_designations for des in user_designations)
    
    if not has_role:
        return Response(
            {'success': False, 'error': f'User does not have the {requested_role} role'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get user details
    try:
        extra_info = ExtraInfo.objects.get(user=user)
        department_name = extra_info.department.name if extra_info.department else 'N/A'
    except ExtraInfo.DoesNotExist:
        department_name = 'N/A'
    
    # Success response
    return Response({
        'success': True,
        'role': requested_role,
        'role_label': role_labels.get(requested_role, requested_role),
        'role_description': role_descriptions.get(requested_role, ''),
        'user': {
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'department': department_name,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def rspc_auto_login(request):
    """
    POST /research_procedures/api/rspc-auto-login/
    RSPC Auto-Login - Automatically assigns first available role
    
    Request JSON:
    {
        "username": "username",
        "password": "password"
    }
    
    Response on success (200):
    {
        "success": true,
        "role": "pi",
        "role_label": "Faculty/PI",
        "user": {...}
    }
    
    Response on error: 401/403
    """
    if request.method != 'POST':
        return Response(
            {'success': False, 'error': 'Method not allowed'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    try:
        if isinstance(request.data, dict):
            data = request.data
        else:
            data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return Response(
            {'success': False, 'error': 'Invalid JSON'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return Response(
            {'success': False, 'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Authenticate user
    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {'success': False, 'error': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get user designations
    try:
        designations = HoldsDesignation.objects.filter(user=user).select_related('designation')
        user_designations = [hd.designation.name for hd in designations]
    except:
        user_designations = []
    
    # Role mapping (priority order)
    role_priority = [
        ('rspc_admin', ['rspc_admin'], 'RSPC Administrator'),
        ('dean_rspc', ['dean_rspc'], 'Dean (RSPC)'),
        ('director', ['director'], 'Director'),
        ('hod', ['hod'], 'Head of Department'),
        ('pi', ['faculty_pi', 'Professor', 'Assoc. Prof', 'Asst. Prof'], 'Faculty/PI'),
        ('committee', ['committee'], 'Committee Member'),
    ]
    
    role_labels = {
        'pi': 'Faculty/PI',
        'hod': 'Head of Department',
        'dean_rspc': 'Dean (RSPC)',
        'director': 'Director',
        'rspc_admin': 'RSPC Administrator',
        'committee': 'Committee Member',
    }
    
    # Find first available role (by priority)
    assigned_role = None
    for role_key, required_des, _ in role_priority:
        if any(des in required_des for des in user_designations):
            assigned_role = role_key
            break
    
    if not assigned_role:
        return Response(
            {'success': False, 'error': 'User has no RSPC roles assigned'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get user details
    try:
        extra_info = ExtraInfo.objects.get(user=user)
        department_name = extra_info.department.name if extra_info.department else 'N/A'
    except ExtraInfo.DoesNotExist:
        department_name = 'N/A'
    
    # Success response
    return Response({
        'success': True,
        'role': assigned_role,
        'role_label': role_labels.get(assigned_role, assigned_role),
        'user': {
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'department': department_name,
        }
    }, status=status.HTTP_200_OK)

# ============================================================================
# PROJECT PROPOSAL ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_proposal(request):
    """
    POST /rspc/proposals/submit/
    UC-001: Submit Research Proposal
    """
    serializer = ProjectCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, project = services.submit_research_proposal(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'project_id': project.pid if project else None
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_consultancy(request):
    """
    POST /rspc/consultancy/submit/
    UC-002: Submit Consultancy Proposal
    """
    serializer = ConsultancyProposalSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, project = services.submit_consultancy_proposal(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'project_id': project.pid if project else None
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_draft(request):
    """
    POST /rspc/proposals/draft/
    UC-004: Save Proposal Draft
    """
    serializer = ProjectDraftSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, project = services.save_proposal_draft(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'project_id': project.pid if project else None
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def resubmit_proposal(request, project_id):
    """
    POST/PUT /rspc/proposals/<project_id>/resubmit/
    UC-005: Edit & Resubmit Proposal
    Allows PI to edit and resubmit draft or rejected proposals
    """
    serializer = ProjectResubmitSerializer(
        data=request.data,
        context={'project_id': project_id}
    )
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.resubmit_proposal(
        project_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PROJECT MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_projects(request):
    """
    GET /rspc/projects/
    Get list of projects based on user role
    """
    filters = {}
    if request.GET.get('status'):
        filters['status'] = request.GET.get('status')
    if request.GET.get('dept'):
        filters['dept'] = request.GET.get('dept')
    if request.GET.get('project_type'):
        filters['project_type'] = request.GET.get('project_type')
    
    projects = services.get_projects(get_user_info(request), filters)
    serializer = ProjectListSerializer(projects, many=True)
    username = get_user_info(request)['username']
    primary_role = _get_primary_role(username)

    projects_payload = serializer.data
    for item, obj in zip(projects_payload, projects):
        item['available_actions'] = _project_actions_for_user(obj, username)
    
    return Response({
        'success': True,
        'count': len(projects),
        'role': primary_role,
        'projects': projects_payload,
        # Backward-compat alias for clients expecting DRF-style list payloads
        'results': projects_payload
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_details(request, project_id):
    """
    GET /rspc/projects/<project_id>/
    Get detailed project information
    """
    # Check access
    has_access = services.check_project_access(
        project_id, 
        get_user_info(request)['username']
    )
    
    if not has_access:
        return Response({
            'success': False,
            'error': 'Access denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    project_data = selectors.get_project_details(project_id)
    
    if not project_data:
        return Response({
            'success': False,
            'error': 'Project not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    project_payload = ProjectSerializer(project_data['project']).data
    project_obj = project_data['project']
    budget_obj = project_data.get('budget')

    # Resolve PI display name robustly (fallback to auth user full name)
    pi_display = project_payload.get('pi_name') or project_payload.get('pi_id')
    if not project_payload.get('pi_name') and project_payload.get('pi_id'):
        user = User.objects.filter(username=project_payload['pi_id']).first()
        if user and user.get_full_name():
            pi_display = user.get_full_name()

    # Resolve department robustly (fallback to PI's ExtraInfo.department)
    department = project_payload.get('dept')
    if not department and project_payload.get('pi_id'):
        pi_extra = ExtraInfo.objects.filter(user__username=project_payload['pi_id']).select_related('department').first()
        if pi_extra and pi_extra.department:
            department = pi_extra.department.name

    # Budget fallback chain: sanctioned_amount -> total_budget -> Budget.total_sanctioned -> computed total
    budget_value = project_payload.get('sanctioned_amount') or project_payload.get('total_budget')
    if (budget_value is None or str(budget_value) == '0' or str(budget_value) == '0.00') and budget_obj:
        budget_value = budget_obj.total_sanctioned
        if (budget_value is None or str(budget_value) == '0' or str(budget_value) == '0.00') and hasattr(budget_obj, 'get_total_budget'):
            budget_value = budget_obj.get_total_budget()

    # Start date fallback to submission date to avoid blank display
    start_date = project_payload.get('start_date') or project_payload.get('submission_date')

    # Backward-compatible aliases for frontend variants (snake_case + camelCase)
    project_payload.update({
        # canonical model-like fields with fallback values
        'pi_name': pi_display,
        'dept': department,
        'sponsored_agency': project_payload.get('sponsored_agency') or '',
        'total_budget': float(budget_value) if budget_value is not None else 0,
        'pi': pi_display,
        'piName': pi_display,
        'principal_investigator': pi_display,
        'principalInvestigator': pi_display,
        'principalInvestigatorName': pi_display,
        'principal_investigator_name': pi_display,
        'investigator': pi_display,
        'investigatorName': pi_display,
        'department': department,
        'deptName': department,
        'departmentName': department,
        'dept_name': department,
        'agency': project_payload.get('sponsored_agency'),
        'sponsoredAgency': project_payload.get('sponsored_agency'),
        'fundingAgency': project_payload.get('sponsored_agency'),
        'funding_agency': project_payload.get('sponsored_agency'),
        'sponsor': project_payload.get('sponsored_agency'),
        'budget': float(budget_value) if budget_value is not None else 0,
        'duration_months': project_payload.get('duration'),
        'durationMonths': project_payload.get('duration'),
        'start_date': start_date,
        'startDate': start_date,
    })

    username = get_user_info(request)['username']

    return Response({
        'success': True,
        'role': _get_primary_role(username),
        'available_actions': _project_actions_for_user(project_obj, username),
        'project': project_payload,
        # Legacy flat fields expected by some clients
        'pi': project_payload.get('pi'),
        'pi_name': project_payload.get('pi_name'),
        'department': project_payload.get('department'),
        'dept': project_payload.get('dept'),
        'agency': project_payload.get('agency'),
        'sponsored_agency': project_payload.get('sponsored_agency'),
        'scheme': project_payload.get('scheme'),
        'budget': project_payload.get('budget'),
        'total_budget': project_payload.get('total_budget'),
        'duration': project_payload.get('duration'),
        'start_date': project_payload.get('start_date'),
        # camelCase aliases used by some UI clients
        'piName': project_payload.get('piName'),
        'principalInvestigator': project_payload.get('principalInvestigator'),
        'principalInvestigatorName': project_payload.get('principalInvestigatorName'),
        'investigatorName': project_payload.get('investigatorName'),
        'departmentName': project_payload.get('department'),
        'deptName': project_payload.get('deptName'),
        'sponsoredAgency': project_payload.get('sponsoredAgency'),
        'fundingAgency': project_payload.get('fundingAgency'),
        'funding_agency': project_payload.get('funding_agency'),
        'sponsor': project_payload.get('sponsor'),
        'startDate': project_payload.get('startDate'),
        'durationMonths': project_payload.get('durationMonths'),
        'co_pis': CoPISerializer(project_data['co_pis'], many=True).data,
        'stats': selectors.get_project_stats(project_id)
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_project(request, project_id):
    """
    POST /rspc/projects/<project_id>/register/
    Register Sanctioned Project
    """
    serializer = ProjectRegistrationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.register_project(
        project_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def commence_project(request, project_id):
    """
    POST /rspc/projects/<project_id>/commence/
    Commence Project
    """
    serializer = ProjectCommencementSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.commence_project(
        project_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_project(request, project_id):
    """
    POST /rspc/projects/<project_id>/close/
    UC-010: Close Project
    """
    serializer = ProjectClosureSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.close_project(
        project_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# STAFF MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_staff(request):
    """
    POST /rspc/staff/request/
    UC-007: Request Staff Appointment
    """
    serializer = StaffRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, staff = services.request_staff(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'staff_id': staff.sid if staff else None
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_ad_committee(request):
    """
    POST /rspc/staff/ad-committee/
    UC-026: Create Staff Advertisement & Committee
    """
    serializer = SelectionCommitteeSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.add_ad_committee(
        serializer.validated_data['staff_id'],
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def staff_selection_report(request):
    """
    POST /rspc/staff/selection-report/
    UC-027: Submit Selection Report
    """
    serializer = StaffSelectionReportSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.staff_selection_report(
        serializer.validated_data['staff_id'],
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def committee_action(request, staff_id):
    """
    POST /rspc/staff/<staff_id>/recommend/
    UC-008: Recommend Staff (Committee Member)
    """
    serializer = CommitteeActionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.committee_action(
        staff_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def staff_decision(request, staff_id):
    """
    POST /rspc/staff/<staff_id>/decision/
    Approve Staff Appointment (HOD/RSPC Authority/Section Head)
    """
    serializer = StaffDecisionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.staff_decision(
        staff_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_staff_request(request, staff_id):
    """
    POST /rspc/staff/<staff_id>/withdraw/
    PI withdraws own staff request.
    """
    success, message = services.withdraw_staff_request(
        staff_id,
        get_user_info(request)
    )

    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def staff_document_upload(request, staff_id):
    """
    POST /rspc/staff/<staff_id>/documents/
    UC-009: Upload Staff Joining Documents
    """
    serializer = StaffDocumentSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.staff_document_upload(
        staff_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_staff(request):
    """
    GET /rspc/staff/
    Get staff list based on user role
    """
    filters = {}
    if request.GET.get('approval_status'):
        filters['approval_status'] = request.GET.get('approval_status')
    if request.GET.get('project_id'):
        filters['project_id'] = request.GET.get('project_id')
    if request.GET.get('position_type'):
        filters['position_type'] = request.GET.get('position_type')
    
    staff_list = services.get_staff(get_user_info(request), filters)
    serializer = StaffSerializer(staff_list, many=True)
    
    return Response({
        'success': True,
        'count': len(staff_list),
        'staff': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_staff_positions(request):
    """
    GET /rspc/staff/positions/
    UC-005, UC-008: View Staff Positions
    """
    project_id = request.GET.get('project_id')
    if project_id:
        project_id = int(project_id)
    
    payload = services.get_staff_positions(get_user_info(request), project_id)
    positions = payload.get('positions', [])

    return Response({
        'success': True,
        'count': len(positions),
        **payload
    }, status=status.HTTP_200_OK)


# ============================================================================
# BUDGET MANAGEMENT ENDPOINTS (UC-011: Budget Reallocation)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_budget(request, project_id):
    """
    GET /rspc/budget/{project_id}/
    UC-011: View Project Budget with detailed breakdown
    
    Response includes:
    - Budget allocation per category (manpower, travel, etc.)
    - Current utilization
    - Available balance
    - Utilization percentage
    
    Role-based access:
    - PI: Own projects only
    - HOD: Department projects
    - Dean RSPC: All projects
    - RSPC Admin: All projects
    """
    try:
        username = request.user.username
        project = get_object_or_404(Project, pid=project_id)
        
        # Check role-based access
        user_can_access = budget_services.check_project_access_by_role(
            project_id, 
            username
        )
        
        if not user_can_access:
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get or create budget
        budget, created = Budget.objects.get_or_create(
            project=project,
            defaults={
                'total_sanctioned': project.sanctioned_amount or project.total_budget,
                'current_funds': Decimal('0')
            }
        )
        
        serializer = BudgetDetailSerializer(budget)
        return Response({
            'success': True,
            'budget': serializer.data,
            'project_id': project_id
        }, status=status.HTTP_200_OK)
        
    except Project.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Project {project_id} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reallocate_budget(request, project_id):
    """
    POST /rspc/budget/{project_id}/reallocate/
    UC-011: Request budget reallocation between categories
    
    Enforces BR-RSPC-08: Max 20% reallocation per category per year
    
    Request JSON:
    {
        "from_category": "manpower",
        "to_category": "equipment",
        "amount": 50000,
        "financial_year": "2023-24",
        "justification": "Need to purchase research equipment due to..."
    }
    
    Response includes:
    - Reallocation ID
    - Approval status
    - Whether approval is required (if >20%)
    """
    try:
        username = request.user.username
        project = get_object_or_404(Project, pid=project_id)
        
        # Check if user can modify budget
        user_can_modify = budget_services.can_modify_budget(project_id, username)
        if not user_can_modify:
            return Response({
                'success': False,
                'error': 'You do not have permission to reallocate budget'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validate request
        serializer = BudgetReallocationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create budget
        budget, _ = Budget.objects.get_or_create(
            project=project,
            defaults={
                'total_sanctioned': project.sanctioned_amount or project.total_budget,
                'current_funds': Decimal('0')
            }
        )
        
        # Check 20% reallocation limit (BR-RSPC-08)
        validated_data = serializer.validated_data
        from_category = validated_data['from_category']
        amount = validated_data['amount']
        financial_year = validated_data['financial_year']
        
        # Get category budget for that year
        category_data = getattr(budget, budget_services.get_category_field(from_category), {})
        year_budget = Decimal(str(category_data.get(financial_year, 0)))
        
        # Calculate if reallocation exceeds 20% limit
        if year_budget > 0:
            realloc_percentage = (amount / year_budget) * 100
            requires_approval = realloc_percentage > 20
        else:
            requires_approval = False
        
        # Create reallocation record
        reallocation = BudgetReallocation.objects.create(
            budget=budget,
            from_category=from_category,
            to_category=validated_data['to_category'],
            amount=amount,
            financial_year=financial_year,
            justification=validated_data['justification'],
            requires_approval=requires_approval,
            approval_status='REQUESTED' if requires_approval else 'APPROVED',
            requested_by=username
        )
        
        # If no approval required, implement immediately
        if not requires_approval:
            budget_services.implement_budget_reallocation(reallocation, username)
            notification_msg = "Budget reallocation completed"
        else:
            notification_msg = "Budget reallocation requires approval (exceeds 20% limit)"
            # Send notification to RSPC Admin
            budget_services.send_budget_notification(
                project_id,
                "Budget Reallocation Requires Approval",
                f"Budget reallocation from {from_category} to {validated_data['to_category']} "
                f"exceeds 20% threshold and requires approval.",
                'rspc_admin'
            )
        
        # Send notification to PI
        budget_services.send_budget_notification(
            project_id,
            "Budget Reallocation Request",
            f"Your reallocation request from {from_category} to {validated_data['to_category']} "
            f"for amount {amount} has been {reallocation.approval_status.lower()}.",
            username
        )
        
        serializer_response = BudgetReallocationSerializer(reallocation)
        return Response({
            'success': True,
            'message': notification_msg,
            'reallocation': serializer_response.data
        }, status=status.HTTP_201_CREATED)
        
    except Project.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Project {project_id} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_budget_tracking(request, project_id):
    """
    GET /rspc/budget/{project_id}/tracking/
    UC-011: Get budget utilization tracking
    
    Returns per-category utilization with alerts for >80% usage
    """
    try:
        username = request.user.username
        project = get_object_or_404(Project, pid=project_id)
        
        # Check access
        if not budget_services.check_project_access_by_role(project_id, username):
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        budget = get_object_or_404(Budget, project=project)
        
        # Build tracking data
        tracking_data = {}
        categories = ['manpower', 'travel', 'consumables', 'equipment', 'contingency', 'overhead']
        alerts = []
        
        for category in categories:
            allocated = budget.get_category_budget(category)
            utilized = budget.get_category_utilization(category)
            
            if allocated > 0:
                util_pct = (utilized / allocated) * 100
            else:
                util_pct = 0
            
            tracking_data[category] = {
                'allocated': float(allocated),
                'utilized': float(utilized),
                'available': float(allocated - utilized),
                'utilization_percentage': round(util_pct, 2)
            }
            
            # Alert if >80% utilization
            if util_pct > 80:
                alerts.append({
                    'category': category,
                    'utilization_percentage': round(util_pct, 2),
                    'message': f'{category} budget is {round(util_pct, 2)}% utilized'
                })
        
        return Response({
            'success': True,
            'project_id': project_id,
            'tracking': tracking_data,
            'alerts': alerts,
            'total_utilization_percentage': round(budget.get_utilization_percentage(), 2)
        }, status=status.HTTP_200_OK)
        
    except Project.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Project {project_id} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_budget_utilized(request, project_id):
    """
    POST /rspc/budget/{project_id}/update-utilized/
    UC-011: Update budget utilized amounts
    
    BR-RSPC-11: Only RSPC Admin can update utilized amounts
    
    Request JSON:
    {
        "category": "manpower",
        "amount": 50000,
        "reason": "Quarterly utilization update",
        "financial_year": "2023-24"
    }
    """
    try:
        username = request.user.username
        
        # BR-RSPC-11: Only RSPC Admin can update utilized amounts
        is_rspc_admin = budget_services.is_user_rspc_admin(username)
        if not is_rspc_admin:
            return Response({
                'success': False,
                'error': 'Only RSPC Admin can update utilized amounts (BR-RSPC-11)'
            }, status=status.HTTP_403_FORBIDDEN)
        
        project = get_object_or_404(Project, pid=project_id)
        budget = get_object_or_404(Budget, project=project)
        
        # Validate request
        serializer = BudgetUtilizationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        category = validated_data['category']
        amount = validated_data['amount']
        reason = validated_data['reason']
        financial_year = validated_data.get('financial_year', '2023-24')
        
        # Record old value for history
        old_utilized = budget.get_category_utilization(category)
        
        # Update utilized amounts
        if not budget.utilized_amounts:
            budget.utilized_amounts = {}
        
        if category not in budget.utilized_amounts:
            budget.utilized_amounts[category] = {}
        
        budget.utilized_amounts[category][financial_year] = float(amount)
        budget.modified_by = username
        budget.save()
        
        # Create history record
        BudgetModificationHistory.objects.create(
            budget=budget,
            modification_type='UTILIZATION_UPDATE',
            category=category,
            old_value=float(old_utilized),
            new_value=float(amount),
            change_amount=amount - old_utilized,
            reason=reason,
            modified_by=username
        )
        
        # Check if utilization exceeds 80% and send alert
        util_pct = budget.get_utilization_percentage()
        alerts = []
        if util_pct > 80:
            alerts.append({
                'type': 'HIGH_UTILIZATION',
                'message': f'Budget utilization is now {round(util_pct, 2)}%',
                'category': category
            })
            services.send_budget_notification(
                project_id,
                "Budget Utilization Alert",
                f"{category} budget has exceeded 80% utilization ({round(util_pct, 2)}%)",
                project.pi_id
            )
        
        return Response({
            'success': True,
            'message': 'Budget utilization updated',
            'alerts': alerts,
            'updated_budget': BudgetDetailSerializer(budget).data
        }, status=status.HTTP_200_OK)
        
    except Project.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Project {project_id} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_budget_history(request, project_id):
    """
    GET /rspc/budget/{project_id}/history/
    UC-011: Get budget modification history
    
    Returns all modifications with timestamps and users
    """
    try:
        username = request.user.username
        project = get_object_or_404(Project, pid=project_id)
        
        # Check access
        if not budget_services.check_project_access_by_role(project_id, username):
            return Response({
                'success': False,
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        budget = get_object_or_404(Budget, project=project)
        
        # Get modification history
        history = BudgetModificationHistory.objects.filter(
            budget=budget
        ).order_by('-modified_at')
        
        serializer = BudgetModificationHistorySerializer(history, many=True)
        
        # Get reallocation history
        reallocations = BudgetReallocation.objects.filter(
            budget=budget
        ).order_by('-requested_at')
        
        reallocation_serializer = BudgetReallocationSerializer(reallocations, many=True)
        
        return Response({
            'success': True,
            'project_id': project_id,
            'modifications': serializer.data,
            'reallocations': reallocation_serializer.data
        }, status=status.HTTP_200_OK)
        
    except Project.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Project {project_id} not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# EXPENDITURE MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_expenditure(request):
    """
    POST /rspc/expenditures/
    UC-012: Create Expenditure Request
    """
    serializer = ExpenditureCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, expenditure = services.create_expenditure_request(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'expenditure_id': expenditure.eid if expenditure else None
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_expenditures(request):
    """
    GET /rspc/expenditures/
    UC-012, UC-013: List Expenditures
    """
    filters = {}
    if request.GET.get('project_id'):
        filters['project_id'] = request.GET.get('project_id')
    if request.GET.get('status'):
        filters['status'] = request.GET.get('status')
    if request.GET.get('category'):
        filters['category'] = request.GET.get('category')
    
    expenditures = services.get_expenditures(get_user_info(request), filters)
    serializer = ExpenditureListSerializer(expenditures, many=True)
    
    return Response({
        'success': True,
        'count': len(expenditures),
        'expenditures': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_expenditure_details(request, expenditure_id):
    """
    GET /rspc/expenditures/<expenditure_id>/
    UC-013: Get Expenditure Details
    """
    expenditure_data = services.get_expenditure_details(
        expenditure_id, 
        get_user_info(request)
    )
    
    if expenditure_data:
        return Response({
            'success': True,
            'expenditure': expenditure_data
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': 'Expenditure not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_expenditure_status(request, expenditure_id):
    """
    GET /rspc/expenditures/<expenditure_id>/track/
    UC-013: Track Expenditure Status
    """
    tracking_data = services.track_expenditure_status(
        expenditure_id, 
        get_user_info(request)
    )
    
    if tracking_data:
        return Response({
            'success': True,
            'tracking': tracking_data
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': 'Expenditure not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def approve_expenditure(request, expenditure_id):
    """
    PUT /rspc/expenditures/<expenditure_id>/approve/
    UC-012, UC-013: Approve Expenditure
    """
    serializer = ExpenditureApprovalSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.approve_expenditure(
        expenditure_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def reject_expenditure(request, expenditure_id):
    """
    PUT /rspc/expenditures/<expenditure_id>/reject/
    UC-012, UC-013: Reject Expenditure
    """
    serializer = ExpenditureRejectionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.reject_expenditure(
        expenditure_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expenditure_history(request, expenditure_id):
    """
    GET /rspc/expenditures/<expenditure_id>/history/
    BR-017: View Expenditure History
    """
    history = services.get_expenditure_history(expenditure_id, get_user_info(request))
    
    return Response({
        'success': True,
        'history': history
    }, status=status.HTTP_200_OK)


# ============================================================================
# FUND REQUEST ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_fund(request):
    """
    POST /rspc/funds/request/
    UC-009: Request Funds
    """
    serializer = FundRequestCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, fund_request = services.request_fund(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'fund_id': fund_request.request_id if fund_request else None
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def director_approve_fund(request, fund_id):
    """
    POST /rspc/funds/<fund_id>/director-approve/
    UC-023: Approve Fund (Director)
    """
    serializer = FundApprovalSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.director_approve_fund(
        fund_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PROGRESS REPORT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_progress_report(request):
    """
    POST /rspc/reports/submit/
    UC-006: Submit Progress Report
    """
    serializer = ProgressReportSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.submit_progress_report(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# REPORT GENERATION ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_report(request):
    """
    POST /rspc/reports/generate/
    UC-014: Generate Reports
    """
    serializer = ReportGenerationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, report_data = services.generate_report(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'report': report_data
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def schedule_report(request):
    """
    POST /rspc/reports/schedule/
    UC-014: Schedule Report
    """
    serializer = ReportScheduleSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message, schedule_id = services.schedule_report(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'schedule_id': schedule_id
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_scheduled_reports(request):
    """
    GET /rspc/reports/scheduled/
    UC-014: List Scheduled Reports
    """
    scheduled_reports = services.get_scheduled_reports(get_user_info(request))
    serializer = ScheduledReportSerializer(scheduled_reports, many=True)
    
    return Response({
        'success': True,
        'count': len(scheduled_reports),
        'reports': serializer.data
    }, status=status.HTTP_200_OK)


# ============================================================================
# APPROVAL WORKFLOW ENDPOINTS
# ============================================================================

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def verify_proposal(request, project_id):
    """
    POST /rspc/proposals/<project_id>/verify/
    UC-014: Verify Proposal (Admin)
    """
    username = get_user_info(request)['username']
    roles = get_user_roles(username)
    if not (roles.get('rspc_admin') or roles.get('dean_rspc')):
        return Response({
            'success': False,
            'error': 'Access denied: only RSPC Admin/Dean can verify proposals'
        }, status=status.HTTP_403_FORBIDDEN)

    serializer = ProposalVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.verify_proposal(
        project_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


def dean_action(request, entity_type, entity_id):
    """
    Internal Dean action handler for proposal/fund approve-reject endpoints.
    UC-019: Approve/Reject Proposal (Dean)
    UC-021: Approve/Reject Fund (Dean)
    """
    username = get_user_info(request)['username']
    roles = get_user_roles(username)
    if not roles.get('dean_rspc'):
        return Response({
            'success': False,
            'error': 'Access denied: only Dean RSPC can approve/reject proposals'
        }, status=status.HTTP_403_FORBIDDEN)

    serializer = ApprovalActionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.dean_approve_reject(
        entity_id,
        entity_type,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def dean_proposal_action(request, project_id):
    """POST /rspc/proposals/<project_id>/dean-action/"""
    return dean_action(request, 'project', project_id)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def dean_fund_action(request, fund_id):
    """POST /rspc/funds/<fund_id>/dean-action/"""
    return dean_action(request, 'fund', fund_id)


# ============================================================================
# COMMITTEE MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extend_committee_deadline(request, committee_id):
    """
    POST /rspc/committees/<committee_id>/extend-deadline/
    UC-007: Extend Committee Deadline
    """
    serializer = CommitteeDeadlineSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Validation failed', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success, message = services.extend_committee_deadline(
        committee_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """
    GET /rspc/notifications/
    UC-015: Get Notifications
    """
    is_read = request.GET.get('is_read')
    if is_read is not None:
        is_read = is_read.lower() == 'true'
    
    limit = int(request.GET.get('limit', 50))
    
    notifications = services.get_notifications(
        get_user_info(request),
        is_read=is_read,
        limit=limit
    )
    serializer = NotificationSerializer(notifications, many=True)
    
    return Response({
        'success': True,
        'count': len(notifications),
        'notifications': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    PUT /rspc/notifications/<notification_id>/mark-read/
    UC-015: Mark Notification as Read
    """
    success, message = services.mark_notification_read(
        notification_id,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_copis(request):
    """
    GET /rspc/utils/co-pis/
    UC-001: Get Co-PIs list
    """
    project_id = request.GET.get('project_id')
    
    if project_id:
        co_pis = services.get_project_copis(int(project_id))
        serializer = CoPISerializer(co_pis, many=True)
    else:
        co_pis = services.get_all_copis(get_user_info(request))
        return Response({
            'success': True,
            'count': len(co_pis),
            'co_pis': co_pis
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': True,
        'count': len(co_pis),
        'co_pis': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_faculty_ids(request):
    """
    GET /rspc/utils/faculty-ids/
    UC-001: Get Faculty IDs
    """
    department = request.GET.get('department')
    
    faculty_list = services.get_faculty_ids(department)
    
    return Response({
        'success': True,
        'count': len(faculty_list),
        'faculty': faculty_list
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_ids(request):
    """
    GET /rspc/utils/project-ids/
    UC-005, UC-012: Get Project IDs
    """
    status_filter = request.GET.get('status')
    
    project_ids = services.get_project_ids(
        get_user_info(request), 
        status_filter
    )
    
    return Response({
        'success': True,
        'count': len(project_ids),
        'projects': project_ids
    }, status=status.HTTP_200_OK)


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard(request):
    """
    GET /rspc/dashboard/
    UC-003: View Dashboard
    """
    dashboard_data = services.get_dashboard_data(get_user_info(request))
    serializer = DashboardSerializer(dashboard_data)
    
    return Response({
        'success': True,
        'dashboard': serializer.data
    }, status=status.HTTP_200_OK)


# ============================================================================
# ENHANCED VALIDATION ENDPOINTS (Phase 1)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_pi_eligibility(request, username):
    """
    GET /rspc/utils/validate-pi/<username>/
    BR-RSPC-03: Check if user is eligible to be PI/Co-PI
    """
    pi_details = services.get_pi_validation_details(username)
    serializer = PIEligibilityResponseSerializer(pi_details)
    
    return Response({
        'success': pi_details.get('is_eligible', False),
        'pi_details': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_duration(request):
    """
    POST /rspc/utils/validate-duration/
    BR-RSPC-11: Validate project duration (6-60 months)
    """
    serializer = DurationValidationSerializer(data=request.data)
    
    if not serializer.is_valid():
        is_valid = False
        message = serializer.errors.get('duration', ['Invalid duration'])[0]
    else:
        is_valid, message = services.validate_project_duration(serializer.validated_data['duration'])
    
    return Response({
        'success': is_valid,
        'duration': request.data.get('duration'),
        'message': message,
        'valid_range': {'min': 6, 'max': 60}
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_committee_members(request):
    """
    POST /rspc/utils/validate-committee/
    BR-RSPC-12: Validate committee has minimum 3 PI-eligible members
    """
    serializer = CommitteeSizeValidationSerializer(data=request.data)
    
    if not serializer.is_valid():
        is_valid = False
        message = serializer.errors.get('members', ['Invalid committee'])[0]
    else:
        is_valid, message = services.validate_committee_members(serializer.validated_data['members'])
    
    return Response({
        'success': is_valid,
        'member_count': len(request.data.get('members', [])),
        'message': message,
        'minimum_required': 3
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_budget_reallocation(request):
    """
    POST /rspc/utils/validate-budget-reallocation/
    BR-RSPC-08: Check if reallocation is within 20% limit
    """
    serializer = BudgetReallocationLimitSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    is_valid, message = services.validate_budget_reallocation(
        data['project_id'],
        data['from_category'],
        data['amount'],
        data.get('to_category')
    )
    
    return Response({
        'success': is_valid,
        'amount': str(data['amount']),
        'message': message,
        'limit_percentage': 20
    }, status=status.HTTP_200_OK)


# ============================================================================
# EXPENDITURE WORKFLOW ENDPOINTS (Phase 2 - BR-RSPC-13)
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_expenditure_workflow(request):
    """
    POST /rspc/expenditures/create-with-workflow/
    UC-012, UC-013: Create expenditure with automatic approval workflow
    BR-RSPC-13: Multi-stage approval routing
    """
    serializer = ExpenditureCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    success, message, result = services.create_expenditure_with_approval_workflow(
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message,
            'data': result
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_expenditure_workflow(request, expenditure_id):
    """
    POST /rspc/expenditures/<expenditure_id>/approve-with-workflow/
    BR-RSPC-13: Approve expenditure and route to next approver
    """
    serializer = ExpenditureApprovalSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    success, message = services.approve_expenditure_with_workflow(
        expenditure_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_expenditure_workflow(request, expenditure_id):
    """
    POST /rspc/expenditures/<expenditure_id>/reject-with-workflow/
    BR-RSPC-13: Reject expenditure at current stage
    """
    serializer = ExpenditureApprovalSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    success, message = services.reject_expenditure_with_workflow(
        expenditure_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_approvals(request):
    """
    GET /rspc/dashboard/pending-approvals/
    BR-RSPC-13: Get all pending approvals for current user
    """
    approvals = services.get_pending_approvals(get_user_info(request))
    serializer = PendingApprovalsSerializer(approvals)
    
    return Response({
        'success': True,
        'approvals': serializer.data
    }, status=status.HTTP_200_OK)


# ============================================================================
# BUDGET REALLOCATION ENDPOINTS (Phase 2 - BR-RSPC-08)
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reallocate_budget_with_tracking(request, project_id):
    """
    POST /rspc/budget/<project_id>/reallocate-with-tracking/
    BR-RSPC-08: Reallocate budget with audit trail
    """
    serializer = BudgetReallocateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    success, message = services.reallocate_budget_with_tracking(
        project_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ENHANCED STAFF MANAGEMENT ENDPOINTS (Phase 2 - BR-RSPC-12)
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_staff_committee(request):
    """
    POST /rspc/staff/committee/create/
    BR-RSPC-12: Create staff selection committee with minimum 3 members
    """
    serializer = StaffCommitteeCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    success, message = services.create_staff_selection_committee(
        serializer.validated_data['staff_id'],
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_committee_verdict(request, staff_id):
    """
    POST /rspc/staff/<staff_id>/committee-verdict/
    UC-008: Committee member submits recommendation
    BR-RSPC-15: Conflict of interest declaration
    """
    serializer = CommitteeVerdictSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    success, message = services.submit_committee_verdict(
        staff_id,
        serializer.validated_data,
        get_user_info(request)
    )
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PROJECT LIFECYCLE ENDPOINTS (Phase 2 - BR-RSPC-09)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_lifecycle(request, project_id):
    """
    GET /rspc/projects/<project_id>/lifecycle/
    BR-RSPC-09: Get detailed project lifecycle information
    """
    lifecycle = services.get_project_lifecycle_status(project_id)
    
    if not lifecycle:
        return Response({
            'success': False,
            'error': 'Project not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ProjectLifecycleSerializer(lifecycle)
    
    return Response({
        'success': True,
        'lifecycle': serializer.data
    }, status=status.HTTP_200_OK)


# ============================================================================
# UC-004, UC-005, UC-012, UC-013: PROJECT MANAGEMENT ENDPOINTS
# ============================================================================
# Imported from project_views module for HTTP routing

from .api.project_views import (
    update_project, list_project_versions, get_project_version,
    cancel_project, get_cancellation_details, request_project_cancellation,
    vet_proposal, get_vetting_details, list_pending_vetting, revert_vetting,
    get_department_projects, get_department_summary
)

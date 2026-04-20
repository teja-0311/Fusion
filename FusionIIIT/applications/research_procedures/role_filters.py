"""
RSPC Module - Role-Based Access Control & Data Filtering
Implements role-based visibility rules and operation validation
"""

from django.db.models import Q, F
from django.contrib.auth.models import User
from typing import Optional, Tuple, List, Dict

from applications.globals.models import ExtraInfo, Faculty, HoldsDesignation, Designation
from .models import Project, Budget, Staff, Expenditure, Request


# ============================================================================
# ROLE DETECTION & USER CONTEXT
# ============================================================================

def get_user_roles(username: str) -> Dict[str, bool]:
    """
    Get all RSPC roles for a user
    Returns dict with role names as keys and boolean values
    
    Example:
        {'pi': True, 'hod': True, 'dean_rspc': False, 'director': False, 'rspc_admin': False, 'committee': False}
    """
    roles = {
        'pi': False,
        'hod': False,
        'dean_rspc': False,
        'director': False,
        'rspc_admin': False,
        'committee': False,
    }
    
    try:
        user = User.objects.get(username=username)
        designations = HoldsDesignation.objects.filter(user=user).select_related('designation')
        designation_names = [hd.designation.name for hd in designations]
        
        # Map designations to RSPC roles
        for des in designation_names:
            des_norm = (des or '').strip().lower().replace(' ', '_')

            if des_norm in ['faculty_pi', 'professor', 'assoc._prof', 'assoc_prof', 'asst._prof', 'asst_prof']:
                roles['pi'] = True
            if des_norm == 'hod' or des_norm.startswith('hod') or 'head_of_department' in des_norm:
                roles['hod'] = True
            if des_norm == 'dean_rspc' or (('dean' in des_norm) and ('rspc' in des_norm or 'research' in des_norm)):
                roles['dean_rspc'] = True
            if des_norm == 'director':
                roles['director'] = True
            if des_norm == 'rspc_admin' or ('rspc' in des_norm and 'admin' in des_norm):
                roles['rspc_admin'] = True
            if 'committee' in des_norm:
                roles['committee'] = True
                
    except (User.DoesNotExist, HoldsDesignation.DoesNotExist):
        pass
    
    return roles


def get_user_department(username: str) -> Optional[str]:
    """Get the department ID for a user"""
    try:
        extra_info = ExtraInfo.objects.get(user__username=username)
        if extra_info.department:
            return extra_info.department.id
        return None
    except ExtraInfo.DoesNotExist:
        return None


def get_user_role_and_dept(username: str) -> Tuple[Dict[str, bool], Optional[str]]:
    """
    Get user roles and department ID in one call
    Returns (roles_dict, department_id)
    """
    roles = get_user_roles(username)
    department_id = get_user_department(username)
    return roles, department_id


def get_faculty_by_username(username: str) -> Optional[Faculty]:
    """Get Faculty object for a user"""
    try:
        extra_info = ExtraInfo.objects.get(user__username=username, user_type='faculty')
        return Faculty.objects.get(id=extra_info.id)
    except (ExtraInfo.DoesNotExist, Faculty.DoesNotExist):
        return None


# ============================================================================
# PROJECT VISIBILITY FILTERS
# ============================================================================

def filter_projects_by_role(projects_qs, username: str, role: str):
    """
    Filter projects based on user role
    
    VISIBILITY RULES:
    - PI: Only see projects where they are PI or Co-PI
    - HOD: See all projects in their department
    - DEAN_RSPC: See all projects
    - DIRECTOR: See summaries only (handled at serializer level)
    - RSPC_ADMIN: See all projects
    - COMMITTEE: See only staff selection related projects
    """
    
    roles = get_user_roles(username)
    faculty = get_faculty_by_username(username)
    
    if role == 'pi' and roles['pi'] and faculty:
        # PI sees only their projects as PI or Co-PI
        return projects_qs.filter(
            Q(principal_investigator=faculty) |
            Q(co_principal_investigators=faculty)
        ).distinct()
    
    elif role == 'hod' and roles['hod']:
        # HOD sees projects in their department
        department_id = get_user_department(username)
        if department_id:
            return projects_qs.filter(
                Q(principal_investigator__department_id=department_id) |
                Q(co_principal_investigators__department_id=department_id)
            ).distinct()
    
    elif role == 'dean_rspc' and roles['dean_rspc']:
        # Dean sees all projects
        return projects_qs
    
    elif role == 'director' and roles['director']:
        # Director sees all projects (summary view handled in serializer)
        return projects_qs
    
    elif role == 'rspc_admin' and roles['rspc_admin']:
        # Admin sees all projects
        return projects_qs
    
    elif role == 'committee' and roles['committee']:
        # Committee member sees staff-related projects only
        # Filter for projects where they're involved in staff selection
        return projects_qs.filter(
            staff__committee__members__user__username=username
        ).distinct()
    
    # Default: no projects visible
    return projects_qs.none()


# ============================================================================
# EXPENDITURE VISIBILITY FILTERS
# ============================================================================

def filter_expenditures_by_role(expenditures_qs, username: str, role: str):
    """
    Filter expenditures based on user role
    
    VISIBILITY RULES:
    - PI: See expenditures for their projects only
    - HOD: See expenditures for projects in their department
    - DEAN_RSPC: See expenditures >= 200K (Level 3)
    - DIRECTOR: See summary data only
    - RSPC_ADMIN: See all expenditures
    - COMMITTEE: No visibility
    """
    
    roles = get_user_roles(username)
    faculty = get_faculty_by_username(username)
    
    if role == 'pi' and roles['pi'] and faculty:
        # PI sees expenditures for their projects
        return expenditures_qs.filter(
            project__principal_investigator=faculty
        )
    
    elif role == 'hod' and roles['hod']:
        # HOD sees expenditures in 50-200K range for their department
        department_id = get_user_department(username)
        if department_id:
            return expenditures_qs.filter(
                Q(project__principal_investigator__department_id=department_id) |
                Q(project__co_principal_investigators__department_id=department_id),
                amount__gt=50000,
                amount__lte=200000
            ).distinct()
    
    elif role == 'dean_rspc' and roles['dean_rspc']:
        # Dean sees expenditures > 200K (Level 3 approval)
        return expenditures_qs.filter(amount__gt=200000)
    
    elif role == 'director' and roles['director']:
        # Director sees summary data (aggregate level, not individual)
        return expenditures_qs.none()  # Summaries handled separately
    
    elif role == 'rspc_admin' and roles['rspc_admin']:
        # Admin sees all expenditures
        return expenditures_qs
    
    # Default: no expenditures visible
    return expenditures_qs.none()


# ============================================================================
# STAFF VISIBILITY FILTERS
# ============================================================================

def filter_staff_by_role(staff_qs, username: str, role: str):
    """
    Filter staff positions based on user role
    
    VISIBILITY RULES:
    - PI: See staff requests for their projects
    - HOD: See staff requests for their department, approve/reject
    - DEAN_RSPC: See all staff requests
    - DIRECTOR: Limited visibility
    - RSPC_ADMIN: See all staff records
    - COMMITTEE: See only applications they're reviewing
    """
    
    roles = get_user_roles(username)
    faculty = get_faculty_by_username(username)
    
    if role == 'pi' and roles['pi'] and faculty:
        # PI sees staff for their projects
        return staff_qs.filter(project__principal_investigator=faculty)
    
    elif role == 'hod' and roles['hod']:
        # HOD sees staff requests for their department
        department_id = get_user_department(username)
        if department_id:
            return staff_qs.filter(
                Q(project__principal_investigator__department_id=department_id) |
                Q(project__co_principal_investigators__department_id=department_id)
            ).distinct()
    
    elif role == 'dean_rspc' and roles['dean_rspc']:
        # Dean sees all staff requests
        return staff_qs
    
    elif role == 'director' and roles['director']:
        # Director has limited visibility
        return staff_qs.none()
    
    elif role == 'rspc_admin' and roles['rspc_admin']:
        # Admin sees all staff
        return staff_qs
    
    elif role == 'committee' and roles['committee']:
        # Committee member sees only applications they're reviewing
        return staff_qs.filter(committee__members__user__username=username).distinct()
    
    # Default: no staff visible
    return staff_qs.none()


# ============================================================================
# BUDGET VISIBILITY FILTERS
# ============================================================================

def filter_budget_by_role(budget_qs, username: str, role: str):
    """
    Filter budgets based on user role
    
    VISIBILITY RULES:
    - PI: See budget for their projects
    - HOD: See budget for department projects
    - DEAN_RSPC: See all budgets
    - DIRECTOR: See summaries only
    - RSPC_ADMIN: See all budgets
    - COMMITTEE: No budget visibility
    """
    
    roles = get_user_roles(username)
    faculty = get_faculty_by_username(username)
    
    if role == 'pi' and roles['pi'] and faculty:
        # PI sees budget for their projects
        return budget_qs.filter(project__principal_investigator=faculty)
    
    elif role == 'hod' and roles['hod']:
        # HOD sees budget for their department
        department_id = get_user_department(username)
        if department_id:
            return budget_qs.filter(
                Q(project__principal_investigator__department_id=department_id) |
                Q(project__co_principal_investigators__department_id=department_id)
            ).distinct()
    
    elif role == 'dean_rspc' and roles['dean_rspc']:
        # Dean sees all budgets
        return budget_qs
    
    elif role == 'director' and roles['director']:
        # Director sees summary data (handled separately)
        return budget_qs.none()
    
    elif role == 'rspc_admin' and roles['rspc_admin']:
        # Admin sees all budgets
        return budget_qs
    
    # Default: no budget visible
    return budget_qs.none()


# ============================================================================
# REQUEST VISIBILITY FILTERS
# ============================================================================

def filter_requests_by_role(requests_qs, username: str, role: str):
    """
    Filter requests (funds, staff) based on user role
    
    VISIBILITY RULES:
    - PI: See their own requests
    - HOD: See requests from their department
    - DEAN_RSPC: See all requests needing final approval
    - DIRECTOR: See fund requests only
    - RSPC_ADMIN: See all requests
    - COMMITTEE: No request visibility
    """
    
    roles = get_user_roles(username)
    faculty = get_faculty_by_username(username)
    
    if role == 'pi' and roles['pi'] and faculty:
        # PI sees their own requests
        return requests_qs.filter(project__principal_investigator=faculty)
    
    elif role == 'hod' and roles['hod']:
        # HOD sees requests from their department
        department_id = get_user_department(username)
        if department_id:
            return requests_qs.filter(
                Q(project__principal_investigator__department_id=department_id) |
                Q(project__co_principal_investigators__department_id=department_id)
            ).distinct()
    
    elif role == 'dean_rspc' and roles['dean_rspc']:
        # Dean sees all requests (for final approval)
        return requests_qs
    
    elif role == 'director' and roles['director']:
        # Director sees fund requests only
        return requests_qs.filter(request_type='funds')
    
    elif role == 'rspc_admin' and roles['rspc_admin']:
        # Admin sees all requests
        return requests_qs
    
    # Default: no requests visible
    return requests_qs.none()


# ============================================================================
# OPERATION VALIDATION
# ============================================================================

def can_create_project(username: str) -> Tuple[bool, str]:
    """Check if user can create/submit a project"""
    roles = get_user_roles(username)
    
    if roles['pi']:
        return True, "PI can create projects"
    elif roles['rspc_admin']:
        return True, "RSPC Admin can create projects"
    else:
        return False, "Only PI and RSPC Admin can create projects"


def can_approve_expenditure(username: str, expenditure_amount: float) -> Tuple[bool, str]:
    """
    Check if user can approve an expenditure for given amount
    Returns (can_approve, message)
    """
    roles = get_user_roles(username)
    
    # Level 1: PI approves <= 50K
    if roles['pi'] and expenditure_amount <= 50000:
        return True, "PI can approve expenditures <= ₹50,000"
    
    # Level 2: HOD approves 50K-200K
    elif roles['hod'] and 50000 < expenditure_amount <= 200000:
        return True, "HOD can approve expenditures ₹50,001-₹200,000"
    
    # Level 3: Dean/Admin approves > 200K
    elif (roles['dean_rspc'] or roles['rspc_admin']) and expenditure_amount > 200000:
        return True, "Dean/Admin can approve expenditures > ₹200,000"
    
    # Level 4: Admin can approve anything
    elif roles['rspc_admin']:
        return True, "RSPC Admin can approve any expenditure"
    
    else:
        return False, f"Insufficient permission to approve ₹{expenditure_amount:,.0f}"


def can_manage_staff(username: str, role: str) -> Tuple[bool, str]:
    """Check if user can manage staff for this role"""
    roles = get_user_roles(username)
    
    if role == 'pi' and roles['pi']:
        return True, "PI can request staff"
    elif role == 'hod' and roles['hod']:
        return True, "HOD can approve staff"
    elif role == 'dean_rspc' and roles['dean_rspc']:
        return True, "Dean RSPC can approve staff"
    elif role == 'committee' and roles['committee']:
        return True, "Committee member can review and verdict"
    elif roles['rspc_admin']:
        return True, "RSPC Admin can manage staff"
    else:
        return False, f"User does not have permission for {role} staff operations"


def can_verify_proposal(username: str) -> Tuple[bool, str]:
    """Check if user can verify proposals"""
    roles = get_user_roles(username)
    
    if roles['rspc_admin']:
        return True, "RSPC Admin can verify proposals"
    elif roles['dean_rspc']:
        return True, "Dean RSPC can verify proposals"
    else:
        return False, "Only RSPC Admin and Dean RSPC can verify proposals"


def can_approve_proposal(username: str) -> Tuple[bool, str]:
    """Check if user can approve/reject proposals (final decision)"""
    roles = get_user_roles(username)
    
    if roles['dean_rspc']:
        return True, "Dean RSPC has final approval authority"
    else:
        return False, "Only Dean RSPC can approve proposals"


# ============================================================================
# APPROVAL WORKFLOW VALIDATION
# ============================================================================

def get_next_approver(username: str, expenditure_amount: float, role: str) -> Tuple[Optional[str], str]:
    """
    Get next approver in the chain for an expenditure
    
    Approval chain:
    - <= 50K: PI approves (Level 1)
    - 50K-200K: PI -> HOD (Level 2)
    - > 200K: PI -> HOD -> Dean/Admin (Level 3)
    """
    
    if expenditure_amount <= 50000:
        return 'pi', "Pending PI approval"
    elif expenditure_amount <= 200000:
        return 'hod', "Pending HOD approval (Level 2)"
    else:
        return 'dean_rspc', "Pending Dean/Admin approval (Level 3)"


def validate_committee_composition(committee_members: List[str]) -> Tuple[bool, str]:
    """
    Validate that committee meets minimum requirements
    - Minimum 3 PI-eligible faculty
    - All must have faculty_pi or professor designation
    """
    
    if len(committee_members) < 3:
        return False, "Committee must have at least 3 members"
    
    eligible_count = 0
    for username in committee_members:
        roles = get_user_roles(username)
        if roles['pi']:
            eligible_count += 1
    
    if eligible_count < 3:
        return False, f"Committee must have at least 3 PI-eligible members (found {eligible_count})"
    
    return True, "Committee composition valid"

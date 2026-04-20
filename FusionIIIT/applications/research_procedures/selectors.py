"""
RSPC Module - Database Query Layer (Selectors)
All .objects usage, filters, gets, and complex query annotations reside here
"""

from django.db.models import Q, Count, Sum, Avg
from django.contrib.auth.models import User
from typing import Dict, List, Optional, Any

from applications.globals.models import ExtraInfo, Faculty, DepartmentInfo, HoldsDesignation, Designation
from .role_filters import get_user_roles
from .models import (
    # Research Areas
    ResearchGroup, ResearchArea,
    
    # Sponsored Projects
    FundingAgency, SponsoredProject, ProjectExpenditure,
    ProjectMilestone, ProjectReport,
    
    # Consultancy
    ConsultancyProject,
    
    # Publications & Patents
    Publication, Patent,
    
    # Research Scholars
    ResearchScholar,
    
    # Core Tables
    Project, Budget, Staff, StaffPosition,
    ProjectAccess, FinancialOutlay, StaffAllocation,
    Request, RSPCInventory, Tracking, File,
    Committee, CommitteeVerdict, CoPI,
    Expenditure, Notification, ScheduledReport
)


# ============================================================================
# USER & AUTHENTICATION SELECTORS
# ============================================================================

def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username"""
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def get_extrainfo_by_username(username: str) -> Optional[ExtraInfo]:
    """Get ExtraInfo by username"""
    try:
        return ExtraInfo.objects.get(user__username=username)
    except ExtraInfo.DoesNotExist:
        return None


def get_user_designations(username: str) -> List[str]:
    """Get all designations for a user"""
    try:
        user = User.objects.get(username=username)
        designations = HoldsDesignation.objects.filter(user=user).select_related('designation')
        return [hd.designation.name for hd in designations]
    except (User.DoesNotExist, HoldsDesignation.DoesNotExist):
        return []


def get_user_department(username: str) -> Optional[str]:
    """Get department for a user"""
    extrainfo = get_extrainfo_by_username(username)
    if extrainfo and extrainfo.department:
        return extrainfo.department.name
    return None


def _normalize_department_value(value: Optional[str]) -> str:
    """Normalize department values for loose matching across legacy stored formats."""
    if value is None:
        return ''
    normalized = str(value).strip().lower()
    if normalized.startswith('department:'):
        normalized = normalized.split(':', 1)[1].strip()
    return normalized


def _department_synonyms(normalized: str) -> set:
    """Return known department aliases (short-code/full-name variants)."""
    if not normalized:
        return set()

    synonym_groups = [
        {'cse', 'computer science', 'computer_science', 'computer science engineering', 'computer_science_engineering'},
        {'ece', 'electronics and communication engineering', 'electronics_communication_engineering'},
        {'me', 'mechanical engineering', 'mechanical_engineering'},
        {'sm', 'school of management', 'school_of_management', 'management'},
        {'mt', 'materials engineering', 'metallurgical engineering', 'metallurgy'},
        {'ns', 'natural science', 'natural_science'},
    ]

    for group in synonym_groups:
        if normalized in group:
            return set(group)
    return set()


def _department_aliases(value: Optional[str]) -> set:
    """Expand a department value into comparable aliases (name/id/legacy label)."""
    aliases = set()
    normalized = _normalize_department_value(value)
    if not normalized:
        return aliases

    aliases.add(normalized)
    aliases.update(_department_synonyms(normalized))

    if normalized.isdigit():
        dept_obj = DepartmentInfo.objects.filter(id=int(normalized)).first()
        if dept_obj:
            aliases.add(_normalize_department_value(dept_obj.name))
            aliases.update(_department_synonyms(_normalize_department_value(dept_obj.name)))
    else:
        dept_obj = DepartmentInfo.objects.filter(name__iexact=normalized).first()
        if dept_obj:
            aliases.add(str(dept_obj.id))
            aliases.update(_department_synonyms(_normalize_department_value(dept_obj.name)))

    return aliases


def departments_match(project_dept: Optional[str], user_dept: Optional[str]) -> bool:
    """Check whether project dept and user dept refer to the same department."""
    project_aliases = _department_aliases(project_dept)
    user_aliases = _department_aliases(user_dept)
    return bool(project_aliases and user_aliases and (project_aliases & user_aliases))


def resolve_project_department(project_or_dept: Any) -> Optional[str]:
    """
    Resolve department for a project/dept value.
    Supports legacy records where Project.dept is empty by falling back to PI's department.
    """
    if project_or_dept is None:
        return None

    # If caller passed a project-like object, try project.dept first.
    if hasattr(project_or_dept, 'dept'):
        project = project_or_dept
        project_dept = getattr(project, 'dept', None)
        if _normalize_department_value(project_dept):
            return project_dept

        pi_identifier = str(getattr(project, 'pi_id', '') or '').strip()
        if not pi_identifier:
            return project_dept

        extrainfo = None
        if pi_identifier.isdigit():
            extrainfo = ExtraInfo.objects.select_related('department').filter(id=int(pi_identifier)).first()
        else:
            extrainfo = ExtraInfo.objects.select_related('department').filter(user__username=pi_identifier).first()

        if extrainfo and extrainfo.department:
            return extrainfo.department.name
        return project_dept

    # Already a plain dept string/value.
    return project_or_dept


def user_department_matches_project(username: str, project_or_dept: Any) -> bool:
    """Check if a project belongs to the user's department."""
    project_dept = resolve_project_department(project_or_dept)
    return departments_match(project_dept, get_user_department(username))


def _user_project_identity_candidates(username: str) -> List[str]:
    """
    Return candidate identifiers that may be stored in Project.pi_id / ProjectAccess.copi_id.
    Handles both username and legacy ExtraInfo.id usage.
    """
    candidates = {username}
    extrainfo = get_extrainfo_by_username(username)
    if extrainfo and extrainfo.id:
        candidates.add(str(extrainfo.id))
    return list(candidates)


def user_matches_project_pi(username: str, project_pi_id: Optional[str]) -> bool:
    """Check whether the given project PI identifier maps to the username."""
    if not project_pi_id:
        return False
    return str(project_pi_id) in _user_project_identity_candidates(username)


def get_user_type(username: str) -> Optional[str]:
    """Get user type (faculty/student/staff)"""
    extrainfo = get_extrainfo_by_username(username)
    if extrainfo:
        return extrainfo.user_type
    return None


def is_faculty(username: str) -> bool:
    """Check if user is faculty"""
    return get_user_type(username) == 'faculty'


def get_faculty_by_username(username: str) -> Optional[Faculty]:
    """Get faculty by username"""
    try:
        extrainfo = ExtraInfo.objects.get(user__username=username, user_type='faculty')
        return Faculty.objects.get(id=extrainfo)
    except (ExtraInfo.DoesNotExist, Faculty.DoesNotExist):
        return None


def get_faculty_by_id(faculty_id) -> Optional[Faculty]:
    """Get faculty by ID"""
    try:
        return Faculty.objects.get(id=faculty_id)
    except Faculty.DoesNotExist:
        return None


def get_all_faculty_ids(department: Optional[str] = None) -> List[Dict]:
    """Get list of faculty IDs for dropdowns (BR-RSPC-02: Only faculty users)"""
    queryset = Faculty.objects.select_related('id__user', 'id__department').filter(
        id__user_type='faculty'   # Only faculty users
    )
    
    if department:
        queryset = queryset.filter(id__department__name=department)
    
    faculty_list = []
    for f in queryset:
        # Only include faculty with assigned department (requirement for proposals)
        if f.id.department:
            faculty_list.append({
                'id': f.id.id,
                'username': f.id.user.username,
                'name': f.id.user.get_full_name(),
                'department': f.id.department.name
            })

    # Fallback: include PI-eligible users even when Faculty mapping is incomplete.
    # This keeps PI dropdown usable in partially seeded test data.
    eligible_designations = {'faculty_pi', 'professor', 'assoc._prof', 'assoc_prof', 'asst._prof', 'asst_prof'}
    user_designation_map: Dict[str, set] = {}
    for hd in HoldsDesignation.objects.select_related('user', 'designation').all():
        des_norm = (hd.designation.name or '').strip().lower().replace(' ', '_')
        user_designation_map.setdefault(hd.user.username, set()).add(des_norm)

    existing_usernames = {f['username'] for f in faculty_list}
    extra_qs = ExtraInfo.objects.select_related('user', 'department').all()
    for extra in extra_qs:
        username = extra.user.username
        if username in existing_usernames:
            continue
        if not (user_designation_map.get(username, set()) & eligible_designations):
            continue

        dept_name = extra.department.name if extra.department else None
        if department and dept_name != department:
            continue

        faculty_list.append({
            'id': extra.id,
            'username': username,
            'name': extra.user.get_full_name() or username,
            'department': dept_name
        })

    faculty_list.sort(key=lambda x: (x.get('name') or '').lower())
    return faculty_list


def get_user_by_designation(designation_name: str) -> List[Dict]:
    """Get users with specific designation"""
    try:
        designation = Designation.objects.get(name=designation_name)
        holdings = HoldsDesignation.objects.filter(
            designation=designation
        ).select_related('user')
        
        return [
            {
                'username': h.user.username,
                'name': h.user.get_full_name(),
                'designation': designation_name
            }
            for h in holdings
        ]
    except Designation.DoesNotExist:
        return []


# ============================================================================
# PROJECT SELECTORS
# ============================================================================

def get_project_by_id(project_id: int) -> Optional[Project]:
    """Get project by ID"""
    try:
        return Project.objects.get(pid=project_id)
    except Project.DoesNotExist:
        return None


def get_projects_for_user(username: str, filters: Optional[Dict] = None) -> List[Project]:
    """
    Get projects based on user role
    - PI sees their own projects
    - HOD sees department projects
    - DEAN_RSPC sees all projects
    - RSPC Admin sees all projects
    - Others see based on access
    """
    roles = get_user_roles(username)
    user_type = get_user_type(username)

    queryset = Project.objects.all().order_by('-created_at')
    
    # Apply filters
    if filters:
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        if filters.get('dept'):
            dept_filter = str(filters['dept']).strip()
            if dept_filter and dept_filter.lower() != 'mine':
                queryset = queryset.filter(dept=dept_filter)
        if filters.get('project_type'):
            queryset = queryset.filter(type=filters['project_type'])
    
    # Role-based filtering
    if roles['dean_rspc'] or roles['rspc_admin']:
        # DEAN RSPC and RSPC Admin see all projects
        return list(queryset)
    elif roles['hod']:
        # HOD sees projects in their department
        dept = get_user_department(username)
        if dept:
            dept_match = Q(dept__iexact=dept) | Q(dept__iexact=f'department: {dept}')
            dept_obj = DepartmentInfo.objects.filter(name__iexact=dept).first()
            if dept_obj:
                dept_match = dept_match | Q(dept=str(dept_obj.id))
            return list(queryset.filter(dept_match))
        return list(queryset.filter(pi_id=username))
    elif roles['pi'] or user_type == 'faculty':
        # Faculty sees projects where they are PI (username/id) or Co-PI
        identity_keys = _user_project_identity_candidates(username)
        copi_project_ids = ProjectAccess.objects.filter(copi_id__in=identity_keys).values_list('pid_id', flat=True)
        return list(queryset.filter(Q(pi_id__in=identity_keys) | Q(pid__in=copi_project_ids)).distinct())
    else:
        # Default: show only if PI
        identity_keys = _user_project_identity_candidates(username)
        copi_project_ids = ProjectAccess.objects.filter(copi_id__in=identity_keys).values_list('pid_id', flat=True)
        return list(queryset.filter(Q(pi_id__in=identity_keys) | Q(pid__in=copi_project_ids)).distinct())


def get_project_details(project_id: int) -> Dict:
    """Get detailed project information with related data"""
    project = get_project_by_id(project_id)
    if not project:
        return {}
    
    # Get Co-PIs
    co_pis = list(ProjectAccess.objects.filter(pid=project))
    
    # Get budget
    try:
        budget = Budget.objects.get(project=project)
    except Budget.DoesNotExist:
        budget = None
    
    # Get financial outlay
    financial_outlay = list(FinancialOutlay.objects.filter(project=project))
    
    # Get staff
    staff = list(Staff.objects.filter(pid=project))
    
    # Get requests
    requests = list(Request.objects.filter(project=project))
    
    # Get expenditures
    expenditures = list(Expenditure.objects.filter(project=project))
    
    return {
        'project': project,
        'co_pis': co_pis,
        'budget': budget,
        'financial_outlay': financial_outlay,
        'staff': staff,
        'requests': requests,
        'expenditures': expenditures,
    }


def get_project_ids_for_user(username: str, status_filter: Optional[str] = None) -> List[Dict]:
    """Get list of project IDs for dropdowns"""
    roles = get_user_roles(username)
    user_type = get_user_type(username)
    
    queryset = Project.objects.all()
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if roles['dean_rspc'] or roles['rspc_admin']:
        # DEAN RSPC and RSPC Admin see all
        pass
    elif roles['hod']:
        # HOD sees projects in their department
        dept = get_user_department(username)
        if dept:
            dept_match = Q(dept__iexact=dept) | Q(dept__iexact=f'department: {dept}')
            dept_obj = DepartmentInfo.objects.filter(name__iexact=dept).first()
            if dept_obj:
                dept_match = dept_match | Q(dept=str(dept_obj.id))
            queryset = queryset.filter(dept_match)
        else:
            queryset = queryset.filter(pi_id=username)
    elif roles['pi'] or user_type == 'faculty':
        identity_keys = _user_project_identity_candidates(username)
        copi_project_ids = ProjectAccess.objects.filter(copi_id__in=identity_keys).values_list('pid_id', flat=True)
        queryset = queryset.filter(Q(pi_id__in=identity_keys) | Q(pid__in=copi_project_ids)).distinct()
    else:
        identity_keys = _user_project_identity_candidates(username)
        copi_project_ids = ProjectAccess.objects.filter(copi_id__in=identity_keys).values_list('pid_id', flat=True)
        queryset = queryset.filter(Q(pi_id__in=identity_keys) | Q(pid__in=copi_project_ids)).distinct()
    
    return [
        {
            'pid': p.pid,
            'name': p.name,
            'status': p.status
        }
        for p in queryset
    ]


def get_project_stats(project_id: int) -> Dict:
    """Get project statistics"""
    project = get_project_by_id(project_id)
    if not project:
        return {}
    
    # Count staff
    staff_count = Staff.objects.filter(pid=project).count()
    
    # Sum expenditures
    expenditure_total = Expenditure.objects.filter(
        project=project,
        status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Count requests
    request_count = Request.objects.filter(project=project).count()
    
    # Budget utilization
    try:
        budget = Budget.objects.get(project=project)
        utilization = (expenditure_total / budget.total_sanctioned * 100) if budget.total_sanctioned > 0 else 0
    except Budget.DoesNotExist:
        utilization = 0
    
    return {
        'staff_count': staff_count,
        'expenditure_total': float(expenditure_total),
        'request_count': request_count,
        'budget_utilization': round(utilization, 2),
    }


def check_project_access(project_id: int, username: str) -> bool:
    """Check if user has access to project"""
    project = get_project_by_id(project_id)
    if not project:
        return False
    
    # Get user roles
    roles = get_user_roles(username)
    
    # PI always has access
    if user_matches_project_pi(username, project.pi_id):
        return True
    
    # Check if Co-PI
    if ProjectAccess.objects.filter(pid=project, copi_id__in=_user_project_identity_candidates(username)).exists():
        return True
    
    # RSPC Admin and DEAN RSPC have access to all projects
    if roles['rspc_admin'] or roles['dean_rspc']:
        return True
    
    # HOD has access to department projects
    if roles['hod']:
        dept = get_user_department(username)
        if departments_match(project.dept, dept):
            return True
    
    return False


# ============================================================================
# BUDGET SELECTORS
# ============================================================================

def get_budget_summary(project_id: int) -> Dict:
    """Get complete budget summary for project"""
    try:
        budget = Budget.objects.get(project_id=project_id)
    except Budget.DoesNotExist:
        return {}
    
    # Get expenditures by category
    expenditures = Expenditure.objects.filter(
        project_id=project_id,
        status='APPROVED'
    ).values('category').annotate(total=Sum('amount'))
    
    expenditure_by_category = {e['category']: float(e['total']) for e in expenditures}
    
    # Get financial outlay by year
    outlay = FinancialOutlay.objects.filter(project_id=project_id).values(
        'year', 'category'
    ).annotate(
        allotted=Sum('allotted_amount'),
        utilized=Sum('utilized_amount')
    ).order_by('year')
    
    return {
        'total_budget': float(budget.total_sanctioned),
        'current_funds': float(budget.current_funds),
        'overhead': budget.overhead,
        'manpower': budget.manpower,
        'travel': budget.travel,
        'contingency': budget.contingency,
        'consumables': budget.consumables,
        'equipments': budget.equipment,
        'expenditure_by_category': expenditure_by_category,
        'yearly_outlay': list(outlay),
    }


# ============================================================================
# STAFF SELECTORS
# ============================================================================

def get_staff_for_user(username: str, filters: Optional[Dict] = None) -> List[Staff]:
    """Get staff list based on user role"""
    roles = get_user_roles(username)
    user_type = get_user_type(username)
    
    queryset = Staff.objects.all().select_related('pid').order_by('-submission_date')
    
    if filters:
        if filters.get('approval_status'):
            queryset = queryset.filter(approval_status=filters['approval_status'])
        if filters.get('project_id'):
            queryset = queryset.filter(pid_id=filters['project_id'])
        if filters.get('position_type'):
            queryset = queryset.filter(type=filters['position_type'])
    
    # Role-based filtering
    if roles['dean_rspc'] or roles['rspc_admin']:
        # DEAN RSPC and RSPC Admin see all
        return list(queryset)
    elif roles['hod']:
        # HOD sees staff in their department
        dept = get_user_department(username)
        if dept:
            return [staff for staff in queryset if departments_match(resolve_project_department(staff.pid), dept)]
        return list(queryset.filter(pid__pi_id__in=_user_project_identity_candidates(username)))
    elif roles['pi'] or user_type == 'faculty':
        # Faculty sees staff in their projects
        identity_keys = _user_project_identity_candidates(username)
        project_ids = Project.objects.filter(pi_id__in=identity_keys).values_list('pid', flat=True)
        return list(queryset.filter(pid_id__in=project_ids))
    else:
        return []


def get_staff_positions(project_id: Optional[int] = None) -> List[StaffPosition]:
    """Get staff positions"""
    queryset = StaffPosition.objects.all().select_related('pid')
    
    if project_id:
        queryset = queryset.filter(pid_id=project_id)
    
    return list(queryset)


def _serialize_staff_position(position: StaffPosition) -> Dict:
    project = position.pid
    return {
        'spid': position.spid,
        'pid': project.pid,
        'project_name': project.name,
        'project_pi': project.pi_name or project.pi_id,
        'project_dept': resolve_project_department(project),
        'positions': position.positions or {},
        'incumbents': position.incumbents or {},
        'vacancy': position.vacancy,
    }


def _serialize_staff_record(staff: Staff) -> Dict:
    project = staff.pid
    return {
        'sid': staff.sid,
        'project_id': project.pid if project else None,
        'project_name': project.name if project else None,
        'project_pi': project.pi_name if project else None,
        'project_dept': resolve_project_department(project) if project else None,
        'person': staff.person,
        'type': staff.type,
        'salary': float(staff.salary or 0),
        'duration': staff.duration,
        'approval_status': staff.approval_status,
        'start_date': staff.start_date,
        'submission_date': staff.submission_date,
    }


def _normalize_designation_name(name: str) -> str:
    return (name or '').strip().lower().replace(' ', '_')


def _role_flags_from_designations(designations: List[str], user_type: Optional[str]) -> Dict[str, bool]:
    des_norms = {_normalize_designation_name(d) for d in designations}
    pi_designations = {'faculty_pi', 'professor', 'assoc._prof', 'assoc_prof', 'asst._prof', 'asst_prof'}
    return {
        'pi': bool(des_norms & pi_designations),
        'hod': any(d.startswith('hod') or 'head_of_department' in d for d in des_norms),
        'dean_rspc': any(d == 'dean_rspc' or ('dean' in d and ('rspc' in d or 'research' in d)) for d in des_norms),
        'rspc_admin': any(d == 'rspc_admin' or ('rspc' in d and 'admin' in d) for d in des_norms),
        'director': any(d == 'director' for d in des_norms),
        'staff': (user_type or '').strip().lower() == 'staff',
    }


def _build_employee_summary(extra_infos: List[ExtraInfo], current_dept: Optional[str] = None) -> Dict:
    usernames = [ei.user.username for ei in extra_infos if ei.user]
    designation_map: Dict[str, List[str]] = {}
    holdings = HoldsDesignation.objects.filter(user__username__in=usernames).select_related('user', 'designation')
    for holding in holdings:
        designation_map.setdefault(holding.user.username, []).append(holding.designation.name)

    employee_details = []
    pi_count = hod_count = staff_count = 0

    for ei in extra_infos:
        if not ei.user:
            continue
        username = ei.user.username
        designations = designation_map.get(username, [])
        flags = _role_flags_from_designations(designations, ei.user_type)
        pi_count += int(flags['pi'])
        hod_count += int(flags['hod'])
        staff_count += int(flags['staff'])
        role_labels = [k for k, v in flags.items() if v]
        employee_details.append({
            'username': username,
            'name': ei.user.get_full_name() or username,
            'user_type': ei.user_type,
            'department': ei.department.name if ei.department else None,
            'designations': designations,
            'roles': role_labels,
        })

    return {
        'department': current_dept,
        'total_employees': len(employee_details),
        'pi_count': pi_count,
        'hod_count': hod_count,
        'staff_count': staff_count,
        'employee_details': employee_details,
    }


def get_staff_positions_for_user(username: str, project_id: Optional[int] = None) -> Dict:
    """
    Get staff positions with role-aware visibility and employee summaries.
    - PI/faculty: project-specific positions for own projects.
    - HOD: department project positions + department employee summary.
    - RSPC Admin/Dean: all positions + institute-wide employee summary.
    """
    roles = get_user_roles(username)
    user_type = get_user_type(username)
    user_dept = get_user_department(username)
    identity_keys = _user_project_identity_candidates(username)
    has_pi_projects = Project.objects.filter(pi_id__in=identity_keys).exists()

    queryset = StaffPosition.objects.all().select_related('pid')
    if project_id:
        queryset = queryset.filter(pid_id=project_id)

    if roles['dean_rspc'] or roles['rspc_admin']:
        positions = list(queryset)
        scope_role = 'admin'
    elif roles['hod']:
        if user_dept:
            positions = [p for p in queryset if departments_match(resolve_project_department(p.pid), user_dept)]
        else:
            positions = list(queryset.none())
        scope_role = 'hod'
    elif roles['pi'] or user_type == 'faculty' or has_pi_projects:
        positions = list(queryset.filter(pid__pi_id__in=identity_keys))
        scope_role = 'pi'
    else:
        positions = []
        scope_role = 'user'

    response = {
        'positions': [_serialize_staff_position(p) for p in positions],
        'scope': {
            'role': scope_role,
            'department': user_dept,
        },
    }

    staff_queryset = Staff.objects.all().select_related('pid').order_by('-submission_date', '-sid')
    if project_id:
        staff_queryset = staff_queryset.filter(pid_id=project_id)

    if scope_role == 'admin':
        visible_staff = list(staff_queryset)
    elif scope_role == 'hod':
        visible_staff = [s for s in staff_queryset if departments_match(resolve_project_department(s.pid), user_dept)]
    elif scope_role == 'pi':
        visible_staff = list(staff_queryset.filter(pid__pi_id__in=identity_keys))
    else:
        visible_staff = []

    response['staff_records'] = [_serialize_staff_record(s) for s in visible_staff]

    all_extra_infos = list(ExtraInfo.objects.select_related('user', 'department').all())

    if scope_role in ['pi', 'hod'] and user_dept:
        dept_extra_infos = [
            ei for ei in all_extra_infos
            if ei.department and departments_match(ei.department.name, user_dept)
        ]
        response['department_employee_summary'] = _build_employee_summary(dept_extra_infos, user_dept)

    if scope_role == 'admin':
        non_student_extra_infos = [
            ei for ei in all_extra_infos
            if (ei.user_type or '').strip().lower() != 'student'
        ]
        institute_summary = _build_employee_summary(non_student_extra_infos, None)
        by_department: Dict[str, Dict[str, int]] = {}
        for emp in institute_summary['employee_details']:
            dept_name = emp.get('department') or 'Unassigned'
            dept_row = by_department.setdefault(
                dept_name,
                {'department': dept_name, 'total_employees': 0, 'pi_count': 0, 'hod_count': 0, 'staff_count': 0}
            )
            dept_row['total_employees'] += 1
            roles_set = set(emp.get('roles') or [])
            dept_row['pi_count'] += int('pi' in roles_set)
            dept_row['hod_count'] += int('hod' in roles_set)
            dept_row['staff_count'] += int('staff' in roles_set)

        institute_summary['departments'] = sorted(by_department.values(), key=lambda x: x['department'])
        response['institute_employee_summary'] = institute_summary

    return response


def get_staff_by_id(staff_id: int) -> Optional[Staff]:
    """Get staff by ID"""
    try:
        return Staff.objects.get(sid=staff_id)
    except Staff.DoesNotExist:
        return None


def get_staff_allocation_by_id(allocation_id: int) -> Optional[StaffAllocation]:
    """Get staff allocation by ID"""
    try:
        return StaffAllocation.objects.get(allocation_id=allocation_id)
    except StaffAllocation.DoesNotExist:
        return None


def get_staff_allocations_for_project(project_id: int) -> List[StaffAllocation]:
    """Get staff allocations for project"""
    return list(StaffAllocation.objects.filter(project_id=project_id).order_by('year'))


# ============================================================================
# FINANCIAL OUTLAY SELECTORS
# ============================================================================

def get_financial_outlay_for_project(project_id: int) -> List[FinancialOutlay]:
    """Get financial outlay for project"""
    return list(FinancialOutlay.objects.filter(project_id=project_id).order_by('category', 'year'))


def get_financial_outlay_grouped(project_id: int) -> Dict:
    """Get financial outlay grouped by category and year"""
    outlay_records = get_financial_outlay_for_project(project_id)
    
    # Group by category
    categories = {}
    for record in outlay_records:
        if record.category not in categories:
            categories[record.category] = {}
        
        if record.year not in categories[record.category]:
            categories[record.category][record.year] = {
                'allotted': float(record.allotted_amount),
                'utilized': float(record.utilized_amount),
                'sub_category': record.sub_category
            }
    
    # Get unique years
    years = sorted(set(r.year for r in outlay_records))
    
    return {
        'categories': categories,
        'years': years
    }


# ============================================================================
# REQUEST SELECTORS
# ============================================================================

def get_requests_for_user(username: str, request_type: Optional[str] = None) -> List[Request]:
    """Get requests based on user role"""
    roles = get_user_roles(username)
    user_type = get_user_type(username)
    
    if request_type == 'funds':
        queryset = RSPCInventory.objects.all().select_related('project')
    else:
        queryset = Request.objects.all().select_related('project')
    
    if request_type == 'funds':
        if roles['dean_rspc'] or roles['rspc_admin']:
            return list(queryset)
        elif roles['pi'] or user_type == 'faculty':
            project_ids = Project.objects.filter(pi_id=username).values_list('pid', flat=True)
            return list(queryset.filter(project_id__in=project_ids))
        else:
            return []
    else:
        if request_type:
            queryset = queryset.filter(request_type=request_type)
        
        if roles['dean_rspc'] or roles['rspc_admin']:
            return list(queryset)
        elif roles['pi'] or user_type == 'faculty':
            project_ids = Project.objects.filter(pi_id=username).values_list('pid', flat=True)
            return list(queryset.filter(project_id__in=project_ids))
        else:
            return []


def get_requests_for_project(project_id: int, request_type: Optional[str] = None) -> List:
    """Get requests for specific project"""
    if request_type == 'funds':
        return list(RSPCInventory.objects.filter(project_id=project_id))
    else:
        queryset = Request.objects.filter(project_id=project_id)
        if request_type:
            queryset = queryset.filter(request_type=request_type)
        return list(queryset)


# ============================================================================
# FILE TRACKING SELECTORS
# ============================================================================

def get_file_by_id(file_id: int) -> Optional[File]:
    """Get file by ID"""
    try:
        return File.objects.get(id=file_id)
    except File.DoesNotExist:
        return None


def get_tracking_for_file(file_id: int) -> List[Tracking]:
    """Get tracking history for file"""
    return list(Tracking.objects.filter(file_id=file_id).order_by('-receive_date'))


def get_inbox_for_user(username: str, designation: Optional[str] = None) -> List[Tracking]:
    """Get inbox files for user filtered by designation"""
    queryset = Tracking.objects.filter(
        receiver_id=username,
        src_module='research_procedures'
    ).select_related('file').order_by('-receive_date')
    
    if designation:
        queryset = queryset.filter(receive_design=designation)
    
    return list(queryset)


def get_current_holder(file_id: int) -> Optional[str]:
    """Get current holder of file"""
    latest = Tracking.objects.filter(file_id=file_id).order_by('-receive_date').first()
    if latest:
        return latest.current_id or latest.receiver_id
    return None


# ============================================================================
# COMMITTEE SELECTORS
# ============================================================================

def get_committee_by_id(committee_id: int) -> Optional[Committee]:
    """Get committee by ID"""
    try:
        return Committee.objects.get(committee_id=committee_id)
    except Committee.DoesNotExist:
        return None


def get_committee_verdicts(committee_id: int) -> List[CommitteeVerdict]:
    """Get all verdicts for committee"""
    return list(CommitteeVerdict.objects.filter(committee_id=committee_id))


def check_unanimous_approval(committee_id: int) -> bool:
    """Check if committee has unanimous approval"""
    verdicts = get_committee_verdicts(committee_id)
    if not verdicts:
        return False
    
    return all(v.decision == 'APPROVE' for v in verdicts)


# ============================================================================
# Co-PI SELECTORS
# ============================================================================

def get_copis_for_project(project_id: int) -> List[ProjectAccess]:
    """Get Co-PIs for specific project"""
    return list(ProjectAccess.objects.filter(pid_id=project_id))


def get_all_copis_for_user(username: str) -> List[Dict]:
    """Get all Co-PIs user can access"""
    roles = get_user_roles(username)
    user_type = get_user_type(username)
    
    if roles['dean_rspc'] or roles['rspc_admin']:
        # DEAN RSPC and RSPC Admin see all
        projects = Project.objects.all()
    elif roles['hod']:
        # HOD sees projects in their department
        dept = get_user_department(username)
        if dept:
            projects = Project.objects.filter(dept=dept)
        else:
            projects = Project.objects.filter(pi_id=username)
    elif roles['pi'] or user_type == 'faculty':
        # Faculty sees Co-PIs in their projects
        projects = Project.objects.filter(pi_id=username)
    else:
        return []
    
    copis = []
    for project in projects:
        project_copis = get_copis_for_project(project.pid)
        for copi in project_copis:
            copis.append({
                'project_id': project.pid,
                'project_name': project.name,
                'copi_id': copi.copi_id,
                'name': copi.name if hasattr(copi, 'name') else copi.copi_id,
                'type': copi.type,
                'affiliation': copi.affiliation,
            })
    
    return copis


# ============================================================================
# EXPENDITURE SELECTORS
# ============================================================================

def get_expenditure_by_id(expenditure_id: int) -> Optional[Expenditure]:
    """Get expenditure by ID"""
    try:
        return Expenditure.objects.get(eid=expenditure_id)
    except Expenditure.DoesNotExist:
        return None


def get_expenditures_for_user(username: str, filters: Optional[Dict] = None) -> List[Expenditure]:
    """Get expenditures based on user role"""
    roles = get_user_roles(username)
    user_type = get_user_type(username)
    
    queryset = Expenditure.objects.all().select_related('project').order_by('-request_date')
    
    if filters:
        if filters.get('project_id'):
            queryset = queryset.filter(project_id=filters['project_id'])
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        if filters.get('category'):
            queryset = queryset.filter(category=filters['category'])
    
    # Role-based filtering
    if roles['dean_rspc'] or roles['rspc_admin']:
        return list(queryset)
    elif roles['hod']:
        # HOD sees expenditures in 50-200K range for their department
        dept = get_user_department(username)
        if dept:
            return list(queryset.filter(
                Q(project__dept=dept),
                amount__gt=50000,
                amount__lte=200000
            ))
        project_ids = Project.objects.filter(pi_id=username).values_list('pid', flat=True)
        return list(queryset.filter(project_id__in=project_ids))
    elif roles['pi'] or user_type == 'faculty':
        project_ids = Project.objects.filter(pi_id=username).values_list('pid', flat=True)
        return list(queryset.filter(project_id__in=project_ids))
    else:
        return []


def get_expenditure_details(expenditure_id: int) -> Dict:
    """Get detailed expenditure information"""
    expenditure = get_expenditure_by_id(expenditure_id)
    if not expenditure:
        return {}
    
    return {
        'eid': expenditure.eid,
        'project': {
            'pid': expenditure.project.pid,
            'name': expenditure.project.name,
            'pi_name': expenditure.project.pi_name,
        },
        'category': expenditure.category,
        'amount': float(expenditure.amount),
        'purpose': expenditure.purpose,
        'status': expenditure.status,
        'requested_by': expenditure.requested_by,
        'requested_at': expenditure.request_date,
        'current_approver': expenditure.current_approver,
        'supporting_documents': expenditure.supporting_documents,
    }


def track_expenditure_status(expenditure_id: int) -> Dict:
    """Track expenditure approval status"""
    expenditure = get_expenditure_by_id(expenditure_id)
    if not expenditure:
        return {}
    
    # Get workflow logs (if any)
    # This would integrate with WorkflowLog model if available
    
    return {
        'eid': expenditure.eid,
        'status': expenditure.status,
        'current_approver': expenditure.current_approver,
        'requested_at': expenditure.request_date,
        'timeline': [
            {
                'status': 'REQUESTED',
                'date': expenditure.request_date,
                'actor': expenditure.requested_by,
            }
        ],
        'escalation_status': 'NORMAL',
    }


# ============================================================================
# NOTIFICATION SELECTORS
# ============================================================================

def get_notifications_for_user(username: str, is_read: Optional[bool] = None, limit: int = 50) -> List[Notification]:
    """Get notifications for user"""
    queryset = Notification.objects.filter(recipient__username=username).order_by('-created_at')
    
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    return list(queryset[:limit])


def get_unread_notification_count(username: str) -> int:
    """Get count of unread notifications"""
    return Notification.objects.filter(recipient__username=username, is_read=False).count()


# ============================================================================
# REPORT SELECTORS
# ============================================================================

def get_scheduled_reports_for_user(username: str) -> List[ScheduledReport]:
    """Get scheduled reports for user"""
    return list(ScheduledReport.objects.filter(created_by=username).order_by('next_run'))


# ============================================================================
# DASHBOARD SELECTORS
# ============================================================================

def get_dashboard_data(username: str) -> Dict:
    """Get dashboard data for user"""
    roles = get_user_roles(username)
    user_type = get_user_type(username)
    designations = get_user_designations(username)
    
    data = {
        'user': {
            'username': username,
            'type': user_type,
            'designations': designations,
        },
        'projects': {
            'total': 0,
            'ongoing': 0,
            'completed': 0,
            'proposed': 0,
        },
        'staff': {
            'total': 0,
            'pending': 0,
            'appointed': 0,
        },
        'notifications': get_unread_notification_count(username),
        'recent_activity': [],
    }
    
    # Get projects
    if roles['dean_rspc'] or roles['rspc_admin']:
        projects = Project.objects.all()
    elif roles['hod']:
        dept = get_user_department(username)
        if dept:
            projects = Project.objects.filter(dept=dept)
        else:
            projects = Project.objects.filter(pi_id=username)
    elif roles['pi'] or user_type == 'faculty':
        projects = Project.objects.filter(pi_id=username)
    else:
        projects = Project.objects.none()
    
    data['projects']['total'] = projects.count()
    data['projects']['ongoing'] = projects.filter(status='ONGOING').count()
    data['projects']['completed'] = projects.filter(status='COMPLETED').count()
    data['projects']['proposed'] = projects.filter(status='PROPOSED').count()
    
    # Get staff
    if roles['dean_rspc'] or roles['rspc_admin']:
        staff = Staff.objects.all()
    elif roles['hod']:
        dept = get_user_department(username)
        if dept:
            staff = Staff.objects.filter(pid__dept=dept)
        else:
            project_ids = projects.values_list('pid', flat=True)
            staff = Staff.objects.filter(pid_id__in=project_ids)
    elif roles['pi'] or user_type == 'faculty':
        project_ids = projects.values_list('pid', flat=True)
        staff = Staff.objects.filter(pid_id__in=project_ids)
    else:
        staff = Staff.objects.none()
    
    data['staff']['total'] = staff.count()
    data['staff']['pending'] = staff.filter(approval_status__contains='PENDING').count()
    data['staff']['appointed'] = staff.filter(approval_status='APPOINTED').count()
    
    # Get recent activity (last 10 tracking entries)
    recent_tracking = Tracking.objects.filter(
        receiver_id=username
    ).select_related('file').order_by('-receive_date')[:5]
    
    for tracking in recent_tracking:
        data['recent_activity'].append({
            'type': 'file',
            'subject': tracking.file.subject if tracking.file else 'Unknown',
            'date': tracking.receive_date,
            'remarks': tracking.remarks,
        })
    
    return data


# ============================================================================
# RESEARCH AREAS SELECTORS
# ============================================================================

def get_research_groups(discipline_id: Optional[int] = None) -> List[ResearchGroup]:
    """Get research groups"""
    queryset = ResearchGroup.objects.filter(is_active=True)
    if discipline_id:
        queryset = queryset.filter(discipline_id=discipline_id)
    return list(queryset)


def get_research_areas(discipline_id: Optional[int] = None) -> List[ResearchArea]:
    """Get research areas"""
    queryset = ResearchArea.objects.filter(is_active=True)
    if discipline_id:
        queryset = queryset.filter(discipline_id=discipline_id)
    return list(queryset)


# ============================================================================
# SPONSORED PROJECTS SELECTORS
# ============================================================================

def get_sponsored_projects_for_faculty(faculty_id) -> List[SponsoredProject]:
    """Get sponsored projects for faculty"""
    return list(SponsoredProject.objects.filter(
        Q(principal_investigator_id=faculty_id) |
        Q(co_principal_investigators=faculty_id)
    ).distinct())


def get_project_expenditures(project_id: int) -> List[ProjectExpenditure]:
    """Get expenditures for sponsored project"""
    return list(ProjectExpenditure.objects.filter(project_id=project_id))


# ============================================================================
# PUBLICATIONS & PATENTS SELECTORS
# ============================================================================

def get_publications_for_faculty(faculty_id) -> Dict:
    """Get publications for faculty"""
    publications = Publication.objects.filter(faculty_authors=faculty_id)
    
    return {
        'total': publications.count(),
        'journals': publications.filter(publication_type='JOURNAL').count(),
        'conferences': publications.filter(publication_type='CONFERENCE').count(),
        'sci_indexed': publications.filter(index_type__in=['SCI', 'SCIE']).count(),
        'recent': list(publications.order_by('-year')[:5]),
    }


def get_patents_for_faculty(faculty_id) -> Dict:
    """Get patents for faculty"""
    patents = Patent.objects.filter(faculty_inventors=faculty_id)
    
    return {
        'total': patents.count(),
        'granted': patents.filter(status='GRANTED').count(),
        'filed': patents.filter(status='FILED').count(),
        'recent': list(patents.order_by('-filing_date')[:5]),
    }


# ============================================================================
# RESEARCH SCHOLARS SELECTORS
# ============================================================================

def get_research_scholars_for_supervisor(faculty_id) -> List[ResearchScholar]:
    """Get research scholars supervised by faculty"""
    from applications.academic_procedures.models import ThesisTopicProcess
    
    thesis_records = ThesisTopicProcess.objects.filter(
        supervisor_id=faculty_id,
        approval_supervisor=True
    ).select_related('student_id')
    
    scholars = []
    for thesis in thesis_records:
        try:
            scholar = ResearchScholar.objects.get(student=thesis.student_id)
            scholars.append(scholar)
        except ResearchScholar.DoesNotExist:
            pass
    
    return scholars


# ============================================================================
# DEPARTMENT STATISTICS
# ============================================================================

def get_department_research_stats(department_name: str) -> Dict:
    """Get research statistics for department"""
    # Get faculty in department
    faculty_ids = ExtraInfo.objects.filter(
        department__name=department_name,
        user_type='faculty'
    ).values_list('id', flat=True)
    
    faculty_list = list(Faculty.objects.filter(id__in=faculty_ids))
    
    # Count publications
    total_publications = Publication.objects.filter(
        faculty_authors__in=faculty_list
    ).distinct().count()
    
    # Count projects
    total_projects = SponsoredProject.objects.filter(
        principal_investigator__in=faculty_list
    ).count()
    
    ongoing_projects = SponsoredProject.objects.filter(
        principal_investigator__in=faculty_list,
        status='ONGOING'
    )
    
    total_funding = sum(p.sanctioned_amount for p in ongoing_projects)
    
    # Count patents
    total_patents = Patent.objects.filter(
        faculty_inventors__in=faculty_list
    ).distinct().count()
    
    granted_patents = Patent.objects.filter(
        faculty_inventors__in=faculty_list,
        status='GRANTED'
    ).distinct().count()
    
    return {
        'department': department_name,
        'faculty_count': len(faculty_list),
        'publications': total_publications,
        'projects': total_projects,
        'ongoing_funding': float(total_funding),
        'patents_total': total_patents,
        'patents_granted': granted_patents,
    }

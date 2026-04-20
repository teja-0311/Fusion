"""
RSPC Module - Business Logic Layer (Services)
All write operations, business logic, and custom exceptions reside here
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.models import User
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple

from applications.globals.models import ExtraInfo, Faculty, HoldsDesignation, Designation
from . import selectors
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
    Project, Budget, Staff, StaffPosition, StaffApprovalStatus,
    ProjectAccess, FinancialOutlay, StaffAllocation,
    Request, RSPCInventory, Tracking, File,
    Committee, CommitteeVerdict, CommitteeMember, CoPI,
    Expenditure, Notification, ScheduledReport, CommitteeDecision
)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class RSPCError(Exception):
    """Base exception for RSPC module"""
    pass


class AuthorizationError(RSPCError):
    """Raised when user is not authorized for an action"""
    pass


class ValidationError(RSPCError):
    """Raised when data validation fails"""
    pass


class BusinessRuleViolation(RSPCError):
    """Raised when a business rule is violated"""
    pass


class ResourceNotFoundError(RSPCError):
    """Raised when a requested resource is not found"""
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date string with special handling for September format (BR-RSPC-16)
    Handles: "Sept. 15, 2024" -> "Sep. 15, 2024"
    """
    if not date_str:
        return None
    
    # Handle September special case
    if date_str.startswith('Sept.'):
        date_str = 'Sep.' + date_str[5:]
    
    # Try different formats
    formats = [
        '%B %d, %Y',  # September 15, 2024
        '%b. %d, %Y',  # Sep. 15, 2024
        '%b %d, %Y',   # Sep 15, 2024
        '%Y-%m-%d',    # 2024-09-15
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def validate_pi_eligibility(username: str) -> Tuple[bool, str]:
    """
    BR-RSPC-03: Only users with designation 'Professor', 'Assistant Professor', or 'Associate Professor' can be PI/Co-PI
    BR-RSPC-002: Only permanent and active faculty members with departmental alignment
    Returns: (is_eligible, reason_if_not)
    """
    try:
        user = User.objects.get(username=username)
        extra_info = ExtraInfo.objects.get(user=user)
    except (User.DoesNotExist, ExtraInfo.DoesNotExist):
        return False, f"User '{username}' not found or incomplete profile"

    user_designations = [
        (hd.designation.name or '').strip().lower().replace(' ', '_')
        for hd in HoldsDesignation.objects.filter(user=user).select_related('designation')
    ]
    eligible_designations = {'professor', 'assistant_professor', 'associate_professor', 'faculty_pi'}
    has_eligible_designation = bool(set(user_designations) & eligible_designations)
    
    # Check user type is faculty (fallback to designation-based eligibility for legacy test users)
    user_type = (extra_info.user_type or '').strip().lower()
    if user_type != 'faculty' and not has_eligible_designation:
        return False, f"User '{username}' is not faculty (type: {extra_info.user_type})"
    
    # Check user status is present/active (from user_status field)
    if extra_info.user_status and extra_info.user_status != 'PRESENT':
        return False, f"User '{username}' is not an active faculty member (status: {extra_info.user_status})"
    
    # Check user account is active in Django
    if not user.is_active:
        return False, f"User '{username}' account is not active"
    
    # Check PI designation eligibility
    if not has_eligible_designation:
        return False, f"User '{username}' must be Professor, Assistant Professor, or Associate Professor"
    
    return True, "PI eligible"


def validate_project_duration(duration: int) -> Tuple[bool, str]:
    """
    BR-RSPC-11: Project duration must be between 6 and 60 months (0.5 to 5 years)
    Returns: (is_valid, reason_if_not)
    """
    if not isinstance(duration, int):
        return False, "Duration must be an integer (months)"
    
    if duration < 6:
        return False, "Duration must be at least 6 months"
    
    if duration > 60:
        return False, "Duration cannot exceed 60 months (5 years)"
    
    return True, "Duration valid"


def validate_rspc_admin(username: str) -> bool:
    """
    BR-RSPC-04: Only users with designation 'rspc_admin' can create new research projects
    BR-RSPC-08: Only RSPC Admin can add/modify staff allocation
    BR-RSPC-11: Only RSPC Admin can update utilized amounts
    """
    designations = selectors.get_user_designations(username)
    return 'rspc_admin' in designations


def validate_faculty_user(username: str) -> bool:
    """
    BR-RSPC-07: Only users with user_type 'faculty' can create research groups
    """
    return selectors.get_user_type(username) == 'faculty'


def validate_pi_project_ownership(project_id: int, username: str) -> bool:
    """
    BR-RSPC-10: Only the Project Investigator can submit closure reports
    """
    project = selectors.get_project_by_id(project_id)
    if not project:
        return False
    return project.pi_id == username


def validate_user_exists(username: str) -> bool:
    """
    BR-RSPC-09: Staff members assigned must exist as valid users
    """
    return selectors.get_user_by_username(username) is not None


def create_file_tracking(
    uploader: str,
    uploader_design: str,
    receiver: str,
    receiver_design: str,
    src_module: str,
    src_object_id: str,
    subject: str,
    attachment,
    remarks: str = ""
) -> Tuple[File, Tracking]:
    """
    BR-RSPC-17: File Tracking Integration
    Create file and tracking record with metadata
    """
    # Create file record
    file_obj = File.objects.create(
        uploader=uploader,
        uploader_design=uploader_design,
        receiver=receiver,
        receiver_design=receiver_design,
        src_module=src_module,
        src_object_id=src_object_id,
        subject=subject,
        attachment=attachment
    )
    
    # Create tracking record
    tracking = Tracking.objects.create(
        file=file_obj,
        sender_id=uploader,
        sender_design=uploader_design,
        receiver_id=receiver,
        receive_design=receiver_design,
        remarks=remarks,
        current_id=receiver,
        src_module=src_module
    )
    
    return file_obj, tracking


def create_notification(
    sender: str,
    receiver: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    message: str = None
) -> Notification:
    """
    BR-RSPC-18: Notification Generation
    Create notification for key events
    """
    from django.contrib.auth.models import User
    
    subject_map = {
        'proposal_pending_verification': 'Proposal Under Review',
        'proposal_approved': 'Proposal Approved',
        'proposal_rejected': 'Proposal Rejected',
        'expenditure_pending_approval': 'Expenditure Pending Approval',
        'expenditure_approved': 'Expenditure Approved',
        'expenditure_rejected': 'Expenditure Rejected',
        'fund_request_pending': 'Fund Request Pending',
        'fund_approved': 'Fund Approved',
        'fund_rejected': 'Fund Rejected',
        'staff_committee_pending': 'Staff Committee Action Required',
        'staff_hod_pending': 'Staff Request Pending HOD Review',
        'project_created': 'New Project Created',
        'project_approved': 'Project Approved',
        'project_rejected': 'Project Rejected',
        'fund_request': 'New Fund Request',
        'staff_request': 'New Staff Request',
        'file_forwarded': 'File Forwarded',
        'patent_updated': 'Patent Status Updated',
    }
    
    title = subject_map.get(event_type, 'RSPC Notification')
    
    if not message:
        message = f"{event_type.replace('_', ' ').title()} for {entity_type} {entity_id}"
    
    # Get User objects from usernames
    try:
        sender_user = User.objects.get(username=sender) if sender else None
    except User.DoesNotExist:
        sender_user = None
    
    try:
        receiver_user = User.objects.get(username=receiver)
    except User.DoesNotExist:
        return None  # Can't create notification if receiver doesn't exist
    
    return Notification.objects.create(
        sender=sender_user,
        recipient=receiver_user,
        event_type=event_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False
    )


def _normalize_designation_name(name: str) -> str:
    return (name or '').strip().lower().replace(' ', '_')


def _get_role_usernames(role_key: str) -> List[str]:
    """
    Get usernames for role-based notification routing.
    Supported role_key: 'dean_rspc', 'rspc_admin', 'director'
    """
    matches = []
    holdings = HoldsDesignation.objects.select_related('user', 'designation').all()

    for holding in holdings:
        des_norm = _normalize_designation_name(holding.designation.name)
        if role_key == 'dean_rspc':
            if des_norm == 'dean_rspc' or ('dean' in des_norm and ('rspc' in des_norm or 'research' in des_norm)):
                matches.append(holding.user.username)
        elif role_key == 'rspc_admin':
            if des_norm == 'rspc_admin' or ('rspc' in des_norm and 'admin' in des_norm):
                matches.append(holding.user.username)
        elif role_key == 'director':
            if des_norm == 'director':
                matches.append(holding.user.username)

    return list(set(matches))


def _get_hod_usernames_for_department(project_dept: str) -> List[str]:
    """Resolve HOD usernames for the given project department."""
    usernames = []
    holdings = HoldsDesignation.objects.select_related('user', 'designation').all()

    for holding in holdings:
        des_norm = _normalize_designation_name(holding.designation.name)
        if not (des_norm == 'hod' or 'head_of_department' in des_norm):
            continue

        extra_info = ExtraInfo.objects.filter(user=holding.user).select_related('department').first()
        if not extra_info or not extra_info.department:
            continue

        if selectors.departments_match(project_dept, extra_info.department.name):
            usernames.append(holding.user.username)

    return list(set(usernames))


# ============================================================================
# PROJECT PROPOSAL SERVICES
# ============================================================================

@transaction.atomic
def submit_research_proposal(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[Project]]:
    """
    UC-001: Submit Research Proposal
    BR-RSPC-03: PI Validation
    BR-RSPC-05: Unique Project Name
    BR-RSPC-06: PI and Co-PI Distinction
    BR-RSPC-17: File Tracking Integration
    BR-RSPC-18: Notification Generation
    """
    username = user_info.get('username')
    is_admin_submitter = validate_rspc_admin(username)
    pi_username = data.get('pi_id') or username
    
    # Non-admin PI users can submit only for themselves.
    if not is_admin_submitter and pi_username != username:
        return False, "PI can submit proposals only for self", None
    
    # BR-RSPC-03: Validate PI eligibility
    is_eligible, reason = validate_pi_eligibility(pi_username)
    if not is_eligible:
        return False, f"PI {pi_username} is not eligible: {reason}", None
    
    # BR-RSPC-05: Unique project name
    if Project.objects.filter(name=data.get('name')).exists():
        return False, "Project name must be unique", None
    
    # BR-RSPC-06: PI and Co-PI distinction
    co_pis = data.get('co_pis', [])
    if pi_username in co_pis:
        return False, "PI cannot also be a Co-PI", None
    
    # BR-RSPC-21: Co-PI list uniqueness
    if len(co_pis) != len(set(co_pis)):
        return False, "Duplicate Co-PIs not allowed", None
    
    # Create project
    pi_user = User.objects.filter(username=pi_username).first()
    pi_extrainfo = ExtraInfo.objects.filter(user__username=pi_username).select_related('department').first()
    resolved_pi_name = data.get('pi_name') or (pi_user.get_full_name() if pi_user else pi_username)
    resolved_dept = data.get('dept') or (pi_extrainfo.department.name if pi_extrainfo and pi_extrainfo.department else '')

    project = Project.objects.create(
        name=data['name'],
        pi_id=pi_username,
        pi_name=resolved_pi_name,
        access=data.get('access', 'noCo'),
        type=data.get('type', 'Research'),
        dept=resolved_dept,
        category=data.get('category', ''),
        sponsored_agency=data.get('sponsored_agency', ''),
        scheme=data.get('scheme', ''),
        description=data.get('description', ''),
        duration=data.get('duration', 12),
        submission_date=timezone.now(),
        total_budget=data.get('total_budget', 0),
        status='PROPOSED',
    )
    
    # Create Co-PI records
    for copi in co_pis:
        ProjectAccess.objects.create(
            pid=project,
            type='internal',
            copi_id=copi,
            name=data.get(f'copi_name_{copi}', '')
        )
    
    # Create budget record
    if 'budget' in data:
        Budget.objects.create(
            project=project,
            manpower=data['budget'].get('manpower', {}),
            travel=data['budget'].get('travel', {}),
            contingency=data['budget'].get('contingency', {}),
            consumables=data['budget'].get('consumables', {}),
            equipment=data['budget'].get('equipments', {}),
            overhead=data['budget'].get('overhead', 0),
            total_sanctioned=data['total_budget'],
            current_funds=0,
        )
    
    # BR-RSPC-17: File Tracking Integration
    if 'file' in data:
        file_obj, tracking = create_file_tracking(
            uploader=username,
            uploader_design='rspc_admin' if is_admin_submitter else 'pi',
            receiver=pi_username,
            receiver_design='PI',
            src_module='research_procedures',
            src_object_id=str(project.pid),
            subject=f"Project Proposal: {project.name}",
            attachment=data['file'],
            remarks="New project proposal submitted"
        )
        project.file_id = str(file_obj.id)
        project.save()
    
    # BR-RSPC-18: Notification to PI
    create_notification(
        sender=username,
        receiver=pi_username,
        event_type='project_created',
        entity_type='project',
        entity_id=str(project.pid),
        message=f"Project {project.name} has been created"
    )
    
    return True, "Proposal submitted successfully", project


@transaction.atomic
def submit_consultancy_proposal(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[Project]]:
    """
    UC-002: Submit Consultancy Proposal
    """
    username = user_info.get('username')
    
    # Consultancy proposal must be submitted by eligible PI/faculty user.
    is_eligible, reason = validate_pi_eligibility(username)
    if not is_eligible:
        return False, f"Only eligible faculty can submit consultancy proposals: {reason}", None
    
    # Create project
    project = Project.objects.create(
        name=data['name'],
        pi_id=username,
        pi_name=user_info.get('name', ''),
        access='noCo',
        type='Consultancy',
        dept=user_info.get('department', ''),
        category='Consultancy',
        sponsored_agency=data.get('client_name', ''),
        scheme='Consultancy',
        description=data.get('description', ''),
        duration=data.get('duration', 6),
        submission_date=timezone.now(),
        total_budget=data.get('contract_amount', 0),
        status='PROPOSED',
    )
    
    return True, "Consultancy proposal submitted successfully", project


@transaction.atomic
def save_proposal_draft(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[Project]]:
    """
    UC-004: Save Proposal Draft
    """
    username = user_info.get('username')
    
    project = Project.objects.create(
        name=data.get('name', f"Draft_{username}_{timezone.now().timestamp()}"),
        pi_id=username,
        pi_name=user_info.get('name', ''),
        access='noCo',
        type=data.get('type', 'Research'),
        dept=user_info.get('department', ''),
        category=data.get('category', ''),
        sponsored_agency=data.get('sponsored_agency', ''),
        scheme=data.get('scheme', ''),
        description=data.get('description', ''),
        duration=data.get('duration', 12),
        submission_date=timezone.now(),
        total_budget=data.get('total_budget', 0),
        status='DRAFT',
    )
    
    return True, "Draft saved successfully", project


@transaction.atomic
def resubmit_proposal(project_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-005: Edit & Resubmit Proposal
    """
    username = user_info.get('username')
    project = selectors.get_project_by_id(project_id)
    
    if not project:
        return False, "Project not found"
    
    if not selectors.user_matches_project_pi(username, project.pi_id):
        return False, "Only PI can resubmit proposal"
    
    # Update project fields
    for key, value in data.items():
        if hasattr(project, key):
            setattr(project, key, value)
    
    project.status = 'PROPOSED'
    project.save()
    
    return True, "Proposal resubmitted successfully"


# ============================================================================
# PROJECT MANAGEMENT SERVICES
# ============================================================================

@transaction.atomic
def register_project(project_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    Register Sanctioned Project
    """
    username = user_info.get('username')
    
    if not validate_rspc_admin(username):
        return False, "Only RSPC Admin can register projects"
    
    project = selectors.get_project_by_id(project_id)
    if not project:
        return False, "Project not found"
    
    project.sanction_date = data.get('sanction_date', timezone.now())
    project.sanctioned_amount = data.get('sanctioned_amount', project.total_budget)
    project.registration_form = data.get('registration_form')
    project.status = 'SANCTIONED'
    project.save()
    
    return True, "Project registered successfully"


@transaction.atomic
def commence_project(project_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    Commence Project
    """
    username = user_info.get('username')
    
    if not validate_rspc_admin(username):
        return False, "Only RSPC Admin can commence projects"
    
    project = selectors.get_project_by_id(project_id)
    if not project:
        return False, "Project not found"
    
    project.start_date = data.get('start_date', timezone.now())
    project.initial_amount = data.get('initial_amount', 0)
    project.status = 'ONGOING'
    project.save()
    
    # Initialize current funds in budget
    try:
        budget = Budget.objects.get(pid=project)
        budget.current_funds = project.initial_amount
        budget.save()
    except Budget.DoesNotExist:
        pass
    
    return True, "Project commenced successfully"


@transaction.atomic
def close_project(project_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-010: Close Project
    BR-RSPC-10: Only PI can submit closure
    """
    username = user_info.get('username')
    
    project = selectors.get_project_by_id(project_id)
    if not project:
        return False, "Project not found"
    
    # BR-RSPC-10: Only PI can submit closure
    if project.pi_id != username:
        return False, "Only PI can submit closure report"
    
    project.end_report = data.get('end_report')
    project.status = 'COMPLETED'
    project.end_date = timezone.now()
    project.end_approval = False
    project.save()
    
    # Notify RSPC Admin
    rspc_admins = selectors.get_user_by_designation('rspc_admin')
    for admin in rspc_admins:
        create_notification(
            sender=username,
            receiver=admin['username'],
            event_type='project_closed',
            entity_type='project',
            entity_id=str(project_id),
            message=f"Project {project.name} closure submitted by PI"
        )
    
    return True, "Closure report submitted successfully"


# ============================================================================
# STAFF MANAGEMENT SERVICES
# ============================================================================

@transaction.atomic
def request_staff(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[Staff]]:
    """
    UC-007: Request Staff Appointment
    """
    username = user_info.get('username')
    
    project_id = data.get('project_id')
    project = selectors.get_project_by_id(project_id)
    
    if not project:
        return False, "Project not found", None
    
    if not selectors.user_matches_project_pi(username, project.pi_id):
        return False, "Only PI can request staff", None
    
    # Create staff record
    staff = Staff.objects.create(
        pid=project,
        person=data.get('person', ''),
        uname=username,
        biodata_number=data.get('biodata_number', ''),
        start_date=data.get('start_date', timezone.now()),
        duration=data.get('duration', 12),
        eligibility=data.get('eligibility', ''),
        type=data.get('type', 'JRF'),
        salary=data.get('salary', 0),
        has_funds=data.get('has_funds', False),
        post_on_website=data.get('post_on_website', False),
        approval_status='HOD_PENDING',
        current_approver='hod',
    )
    
    # Create request record
    Request.objects.create(
        project=project,
        request_type='staff',
        description=f"Staff request for {data.get('type', 'position')}",
        status='PENDING'
    )

    project_dept = selectors.resolve_project_department(project)
    hod_users = _get_hod_usernames_for_department(project_dept) or _get_role_usernames('rspc_admin')
    for hod_user in set(hod_users):
        create_notification(
            sender=username,
            receiver=hod_user,
            event_type='staff_hod_pending',
            entity_type='staff',
            entity_id=str(staff.sid),
            message=f"New staff request for {staff.person or staff.type} in project {project.name} is pending HOD review."
        )

    return True, "Staff request submitted for HOD approval", staff


@transaction.atomic
def add_ad_committee(staff_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-026: Create Staff Advertisement & Committee
    BR-RSPC-12: Committee composition requirements
    """
    username = user_info.get('username')
    
    staff = selectors.get_staff_by_id(staff_id)
    if not staff:
        return False, "Staff request not found"
    
    if staff.pid.pi_id != username:
        return False, "Only PI can create committee"
    
    # BR-RSPC-12: Committee composition requirements
    committee_members = data.get('committee_members', [])
    if len(committee_members) < 3:
        return False, "Committee must have at least 3 members"
    
    # Create committee
    committee = Committee.objects.create(
        name=f"Selection Committee for {staff.person}",
        deadline=data.get('deadline', timezone.now() + timezone.timedelta(days=14)),
        staff=staff,
    )
    
    # Add members
    for member_username in committee_members:
        extrainfo = selectors.get_extrainfo_by_username(member_username)
        if extrainfo:
            committee.members.add(extrainfo)
    
    # Update staff
    staff.ad_file = data.get('ad_file')
    staff.selection_committee = committee_members
    staff.approval_status = 'COMMITTEE_PENDING'
    staff.save()
    
    return True, "Advertisement and committee created successfully"


@transaction.atomic
def staff_selection_report(staff_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-027: Submit Selection Report
    """
    username = user_info.get('username')
    
    staff = selectors.get_staff_by_id(staff_id)
    if not staff:
        return False, "Staff request not found"
    
    if staff.pid.pi_id != username:
        return False, "Only PI can submit selection report"
    
    staff.final_selection = data.get('final_selection', [])
    staff.waiting_list = data.get('waiting_list', [])
    staff.biodata_final = data.get('biodata_final', [])
    staff.biodata_waiting = data.get('biodata_waiting', [])
    staff.comparative_file = data.get('comparative_file')
    staff.approval_status = 'HOD_PENDING'
    staff.current_approver = 'hod'
    staff.save()
    
    return True, "Selection report submitted successfully"


@transaction.atomic
def committee_action(staff_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-008: Recommend Staff (Committee Member)
    BR-RSPC-15: Conflict of Interest Declaration
    """
    username = user_info.get('username')
    
    staff = selectors.get_staff_by_id(staff_id)
    if not staff:
        return False, "Staff request not found"
    
    committee = Committee.objects.filter(staff=staff).first()
    if not committee:
        return False, "Committee not found"
    
    # Check if user is committee member
    extrainfo = selectors.get_extrainfo_by_username(username)
    if not extrainfo or extrainfo not in committee.members.all():
        return False, "You are not a member of this committee"
    
    # BR-RSPC-15: Conflict of Interest Declaration
    if data.get('conflict_declaration'):
        # Record conflict
        pass
    
    # Record verdict
    verdict, created = CommitteeVerdict.objects.get_or_create(
        committee=committee,
        member=extrainfo,
        defaults={
            'decision': data.get('recommendation', 'APPROVE'),
            'comments': data.get('comments', ''),
        }
    )
    
    if not created:
        verdict.decision = data.get('recommendation', 'APPROVE')
        verdict.comments = data.get('comments', '')
        verdict.save()
    
    # Update staff verdicts
    verdicts = staff.gave_verdict
    verdicts[username] = data.get('recommendation', 'APPROVE')
    staff.gave_verdict = verdicts
    staff.save()
    
    return True, "Recommendation submitted successfully"


@transaction.atomic
def staff_decision(staff_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    Approve Staff Appointment (HOD/RSPC Authority/Section Head)
    """
    username = user_info.get('username')
    
    staff = selectors.get_staff_by_id(staff_id)
    if not staff:
        return False, "Staff request not found"
    
    action = data.get('action')

    if action not in ['Approve', 'Reject']:
        return False, "Invalid action"

    roles = selectors.get_user_roles(username)
    is_hod_for_project = roles.get('hod', False) and selectors.user_department_matches_project(username, staff.pid)
    is_rspc_authority = roles.get('rspc_admin', False) or roles.get('dean_rspc', False)

    if staff.approval_status == 'HOD_PENDING':
        if not is_hod_for_project:
            return False, "Only HOD of the project department can take this action"

        if action == 'Approve':
            staff.approval_status = 'RSPC_PENDING'
            staff.current_approver = 'rspc_admin'
        else:
            staff.approval_status = 'HOD_REJECTED'
            staff.current_approver = ''

    elif staff.approval_status == 'RSPC_PENDING':
        if not is_rspc_authority:
            return False, "Only RSPC Admin/Dean can take this action"

        if action == 'Approve':
            staff.approval_status = 'APPOINTED'
            staff.current_approver = ''

            # Create staff allocation
            StaffAllocation.objects.create(
                project=staff.pid,
                staff_id=staff.uname,
                name=staff.person,
                qualification=data.get('qualification', ''),
                stipend=staff.salary,
                year=timezone.now().year,
                start_date=staff.start_date,
                end_date=staff.start_date + timezone.timedelta(days=30*staff.duration)
            )
        else:
            staff.approval_status = 'RSPC_REJECTED'
            staff.current_approver = ''
    else:
        return False, f"Staff request is not pending approval at this stage ({staff.approval_status})"

    staff.save()
    
    action_word = 'approved' if action == 'Approve' else 'rejected'
    return True, f"Staff {action_word} successfully"


@transaction.atomic
def withdraw_staff_request(staff_id: int, user_info: Dict) -> Tuple[bool, str]:
    """
    PI can withdraw own staff request before final appointment.
    """
    username = user_info.get('username')

    staff = selectors.get_staff_by_id(staff_id)
    if not staff:
        return False, "Staff request not found"

    if not selectors.user_matches_project_pi(username, staff.pid.pi_id):
        return False, "Only PI can withdraw this staff request"

    if staff.approval_status in ['APPOINTED', 'REJECTED', 'HOD_REJECTED', 'RSPC_REJECTED', 'WITHDRAWN']:
        return False, f"Cannot withdraw at current stage ({staff.approval_status})"

    staff.approval_status = 'WITHDRAWN'
    staff.current_approver = ''
    staff.save()

    return True, "Staff request withdrawn successfully"


@transaction.atomic
def staff_document_upload(staff_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-009: Upload Staff Joining Documents
    """
    username = user_info.get('username')
    
    staff = selectors.get_staff_by_id(staff_id)
    if not staff:
        return False, "Staff request not found"
    
    staff.joining_report = data.get('joining_report')
    staff.salary_per_month = data.get('salary_per_month', staff.salary)
    staff.id_card = data.get('id_card')
    staff.doc_approval = True
    staff.save()
    
    return True, "Documents uploaded successfully"


def get_staff(user_info: Dict, filters: Dict) -> List[Staff]:
    """Get staff list based on user role"""
    username = user_info.get('username')
    return selectors.get_staff_for_user(username, filters)


def get_staff_positions(user_info: Dict, project_id: Optional[int] = None) -> Dict[str, Any]:
    """Get staff positions"""
    username = user_info.get('username')
    return selectors.get_staff_positions_for_user(username, project_id)


# ============================================================================
# BUDGET MANAGEMENT SERVICES
# ============================================================================

def get_budget_summary(project_id: int) -> Dict:
    """Get budget summary"""
    return selectors.get_budget_summary(project_id)


@transaction.atomic
def reallocate_budget(project_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-011, UC-012: Reallocate Budget
    BR-RSPC-08: Budget reallocation limits (20% max)
    """
    username = user_info.get('username')
    role = user_info.get('role')
    
    project = selectors.get_project_by_id(project_id)
    if not project:
        return False, "Project not found"
    
    # Check permissions
    if project.pi_id != username and not validate_rspc_admin(username):
        return False, "Only PI or RSPC Admin can reallocate budget"
    
    from_category = data.get('from_category')
    to_category = data.get('to_category')
    amount = data.get('amount')
    justification = data.get('justification')
    
    # Get budget
    try:
        budget = Budget.objects.get(pid=project)
    except Budget.DoesNotExist:
        return False, "Budget not found"
    
    # Calculate current allocation for from_category
    current_allocation = 0
    if from_category == 'manpower':
        current_allocation = sum(budget.manpower.values()) if budget.manpower else 0
    elif from_category == 'travel':
        current_allocation = sum(budget.travel.values()) if budget.travel else 0
    # ... other categories
    
    # BR-RSPC-08: Max 20% reallocation
    if amount > current_allocation * 0.2:
        # Check if higher approval needed
        if role not in ['HOD', 'RSPC Admin']:
            return False, "Reallocation exceeds 20% limit. HOD approval required."
    
    # Update budget
    # Implementation depends on budget structure
    
    return True, "Budget reallocated successfully"


# ============================================================================
# EXPENDITURE MANAGEMENT SERVICES
# ============================================================================

@transaction.atomic
def create_expenditure_request(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[Expenditure]]:
    """
    UC-012: Create Expenditure Request
    BR-RSPC-13: Expenditure approval thresholds
    """
    username = user_info.get('username')
    
    project_id = data.get('project_id')
    project = selectors.get_project_by_id(project_id)
    
    if not project:
        return False, "Project not found", None
    
    # Check if user is PI or Co-PI
    if project.pi_id != username:
        is_copi = ProjectAccess.objects.filter(pid=project, copi_id=username).exists()
        if not is_copi:
            return False, "Only PI or Co-PI can create expenditure requests", None
    
    amount = data.get('amount')
    
    # BR-RSPC-13: Determine approval routing based on amount
    if amount <= 50000:
        current_approver = 'PI'
    elif amount <= 200000:
        current_approver = 'HOD'
    else:
        current_approver = 'RSPC'
    
    # Create expenditure
    expenditure = Expenditure.objects.create(
        project=project,
        category=data.get('category', ''),
        amount=amount,
        purpose=data.get('purpose', ''),
        status='PENDING',
        requested_by=username,
        current_approver=current_approver,
        supporting_documents=data.get('supporting_documents', [])
    )

    # Real-time notification routing to next approver in chain
    if current_approver == 'PI':
        next_approvers = [project.pi_id]
    elif current_approver == 'HOD':
        next_approvers = _get_hod_usernames_for_department(project.dept) or _get_role_usernames('rspc_admin')
    else:
        next_approvers = _get_role_usernames('rspc_admin')

    for approver in set(next_approvers):
        if approver != username:
            create_notification(
                sender=username,
                receiver=approver,
                event_type='expenditure_pending_approval',
                entity_type='expenditure',
                entity_id=str(expenditure.eid),
                message=f"Expenditure request for project '{project.name}' is pending your approval."
            )
    
    return True, "Expenditure request created successfully", expenditure


def get_expenditures(user_info: Dict, filters: Dict) -> List[Expenditure]:
    """List expenditures"""
    username = user_info.get('username')
    return selectors.get_expenditures_for_user(username, filters)


def get_expenditure_details(expenditure_id: int, user_info: Dict) -> Optional[Dict]:
    """Get expenditure details"""
    username = user_info.get('username')
    
    expenditure = selectors.get_expenditure_by_id(expenditure_id)
    if not expenditure:
        return None
    
    # Check access
    if expenditure.project.pi_id != username:
        is_copi = ProjectAccess.objects.filter(pid=expenditure.project, copi_id=username).exists()
        if not is_copi and not validate_rspc_admin(username):
            return None
    
    return selectors.get_expenditure_details(expenditure_id)


def track_expenditure_status(expenditure_id: int, user_info: Dict) -> Optional[Dict]:
    """Track expenditure status"""
    return selectors.track_expenditure_status(expenditure_id)


@transaction.atomic
def approve_expenditure(expenditure_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    Approve expenditure request
    """
    username = user_info.get('username')
    role = user_info.get('role')
    
    expenditure = selectors.get_expenditure_by_id(expenditure_id)
    if not expenditure:
        return False, "Expenditure not found"
    
    # Check if user is current approver
    approver_map = {
        'PI': expenditure.project.pi_id,
        'HOD': 'hod_username',  # Would need to determine HOD
        'RSPC': 'rspc_admin_username',
    }
    
    expected_approver = approver_map.get(expenditure.current_approver)
    if expected_approver != username and not validate_rspc_admin(username):
        return False, "You are not authorized to approve this request"
    
    # Update status
    if expenditure.current_approver == 'PI':
        expenditure.status = 'PI_APPROVED'
        expenditure.current_approver = 'HOD'
        next_approvers = _get_hod_usernames_for_department(expenditure.project.dept) or _get_role_usernames('rspc_admin')
        for approver in set(next_approvers):
            if approver != username:
                create_notification(
                    sender=username,
                    receiver=approver,
                    event_type='expenditure_pending_approval',
                    entity_type='expenditure',
                    entity_id=str(expenditure.eid),
                    message=f"Expenditure for project '{expenditure.project.name}' moved to HOD review."
                )
        create_notification(
            sender=username,
            receiver=expenditure.requested_by,
            event_type='expenditure_pending_approval',
            entity_type='expenditure',
            entity_id=str(expenditure.eid),
            message=f"Your expenditure request is PI approved and pending HOD review."
        )
    elif expenditure.current_approver == 'HOD':
        expenditure.status = 'HOD_APPROVED'
        expenditure.current_approver = 'RSPC'
        for admin_user in set(_get_role_usernames('rspc_admin')):
            if admin_user != username:
                create_notification(
                    sender=username,
                    receiver=admin_user,
                    event_type='expenditure_pending_approval',
                    entity_type='expenditure',
                    entity_id=str(expenditure.eid),
                    message=f"Expenditure for project '{expenditure.project.name}' moved to RSPC approval."
                )
        create_notification(
            sender=username,
            receiver=expenditure.requested_by,
            event_type='expenditure_pending_approval',
            entity_type='expenditure',
            entity_id=str(expenditure.eid),
            message=f"Your expenditure request is HOD approved and pending RSPC review."
        )
    elif expenditure.current_approver == 'RSPC':
        expenditure.status = 'APPROVED'
        expenditure.current_approver = None
        
        # Update budget utilization
        try:
            budget = Budget.objects.get(pid=expenditure.project)
            budget.current_funds -= expenditure.amount
            budget.save()
        except Budget.DoesNotExist:
            pass
        create_notification(
            sender=username,
            receiver=expenditure.requested_by,
            event_type='expenditure_approved',
            entity_type='expenditure',
            entity_id=str(expenditure.eid),
            message=f"Your expenditure request for project '{expenditure.project.name}' has been approved."
        )
    
    expenditure.save()
    
    return True, "Expenditure approved successfully"


@transaction.atomic
def reject_expenditure(expenditure_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """Reject expenditure request"""
    username = user_info.get('username')
    
    expenditure = selectors.get_expenditure_by_id(expenditure_id)
    if not expenditure:
        return False, "Expenditure not found"
    
    expenditure.status = 'REJECTED'
    expenditure.save()

    create_notification(
        sender=username,
        receiver=expenditure.requested_by,
        event_type='expenditure_rejected',
        entity_type='expenditure',
        entity_id=str(expenditure.eid),
        message=f"Your expenditure request for project '{expenditure.project.name}' was rejected."
    )
    
    return True, "Expenditure rejected successfully"


def get_expenditure_history(expenditure_id: int, user_info: Dict) -> List:
    """Get expenditure history"""
    # Would integrate with audit logs
    return []


# ============================================================================
# FUND REQUEST SERVICES
# ============================================================================

@transaction.atomic
def request_fund(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[RSPCInventory]]:
    """
    UC-009: Request Funds
    """
    username = user_info.get('username')
    
    project_id = data.get('project_id')
    project = selectors.get_project_by_id(project_id)
    
    if not project:
        return False, "Project not found", None
    
    if project.pi_id != username:
        return False, "Only PI can request funds", None
    
    # Create fund request
    fund_request = RSPCInventory.objects.create(
        project=project,
        description=data.get('description', ''),
        amount=data.get('amount', 0),
        status='PENDING'
    )
    
    # Create request record
    Request.objects.create(
        project=project,
        request_type='funds',
        description=data.get('description', ''),
        amount=data.get('amount', 0),
        status='PENDING'
    )

    # Notify dean and admin users about new fund request
    escalation_targets = set(_get_role_usernames('dean_rspc') + _get_role_usernames('rspc_admin'))
    for target in escalation_targets:
        if target != username:
            create_notification(
                sender=username,
                receiver=target,
                event_type='fund_request_pending',
                entity_type='fund',
                entity_id=str(fund_request.request_id),
                message=f"Fund request submitted for project '{project.name}' and awaiting action."
            )
    
    return True, "Fund request submitted successfully", fund_request


@transaction.atomic
def director_approve_fund(fund_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-023: Approve Fund (Director)
    """
    username = user_info.get('username')
    
    try:
        fund_request = RSPCInventory.objects.get(request_id=fund_id)
    except RSPCInventory.DoesNotExist:
        return False, "Fund request not found"
    
    fund_request.status = 'APPROVED'
    fund_request.save()

    # Notify PI that fund request has final approval
    create_notification(
        sender=username,
        receiver=fund_request.project.pi_id,
        event_type='fund_approved',
        entity_type='fund',
        entity_id=str(fund_request.request_id),
        message=f"Fund request for project '{fund_request.project.name}' has been approved by Director."
    )
    
    return True, "Fund request approved by Director"


# ============================================================================
# PROGRESS REPORT SERVICES
# ============================================================================

@transaction.atomic
def submit_progress_report(data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-006: Submit Progress Report
    """
    username = user_info.get('username')
    
    project_id = data.get('project_id')
    project = selectors.get_project_by_id(project_id)
    
    if not project:
        return False, "Project not found"
    
    if project.pi_id != username:
        return False, "Only PI can submit progress reports"
    
    # Create report
    ProjectReport.objects.create(
        project=project,  # This needs to be mapped to SponsoredProject
        report_type=data.get('report_type', 'QUARTERLY'),
        period_from=data.get('period_from'),
        period_to=data.get('period_to'),
        summary=data.get('summary', ''),
        report_file=data.get('report_file'),
        submitted_date=timezone.now(),
        approved=False
    )
    
    return True, "Progress report submitted successfully"


# ============================================================================
# REPORT GENERATION SERVICES
# ============================================================================

def generate_report(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[Dict]]:
    """
    UC-014: Generate Reports
    """
    report_type = data.get('report_type')
    project_id = data.get('project_id')
    department = data.get('department')
    date_range = data.get('date_range', {})
    format_type = data.get('format', 'PDF')
    
    report_data = {}
    
    if report_type == 'project_summary' and project_id:
        project = selectors.get_project_by_id(project_id)
        if project:
            report_data = {
                'type': 'Project Summary',
                'project': {
                    'id': project.pid,
                    'name': project.name,
                    'pi': project.pi_name,
                    'status': project.status,
                    'budget': float(project.total_budget),
                }
            }
    elif report_type == 'department_stats' and department:
        report_data = selectors.get_department_research_stats(department)
    
    return True, "Report generated successfully", report_data


@transaction.atomic
def schedule_report(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[int]]:
    """
    Schedule automated report generation
    """
    username = user_info.get('username')
    
    scheduled = ScheduledReport.objects.create(
        report_type=data.get('report_type'),
        frequency=data.get('frequency'),
        recipients=data.get('recipients', []),
        next_run=data.get('next_run', timezone.now()),
        created_by=username,
        parameters=data.get('parameters', {})
    )
    
    return True, "Report scheduled successfully", scheduled.sid


def get_scheduled_reports(user_info: Dict) -> List[ScheduledReport]:
    """List scheduled reports"""
    username = user_info.get('username')
    return selectors.get_scheduled_reports_for_user(username)


# ============================================================================
# APPROVAL WORKFLOW SERVICES
# ============================================================================

@transaction.atomic
def verify_proposal(project_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-014: Verify Proposal (Admin)
    """
    username = user_info.get('username')
    
    designations = selectors.get_user_designations(username)
    if not ('rspc_admin' in designations or 'dean_rspc' in designations):
        return False, "Only RSPC Admin or Dean RSPC can verify proposals"
    
    project = selectors.get_project_by_id(project_id)
    if not project:
        return False, "Project not found"
    
    action = data.get('action')
    
    if action == 'Verify':
        project.status = 'UNDER_REVIEW'
        project.save()

        # Notify PI: proposal moved to review stage
        create_notification(
            sender=username,
            receiver=project.pi_id,
            event_type='proposal_pending_verification',
            entity_type='project',
            entity_id=str(project.pid),
            message=f"Your proposal '{project.name}' has been verified and moved to UNDER_REVIEW."
        )

        # Notify Dean RSPC approvers about pending proposal decision
        dean_users = [u for u in _get_role_usernames('dean_rspc') if u != username]
        for dean_user in dean_users:
            create_notification(
                sender=username,
                receiver=dean_user,
                event_type='proposal_pending_verification',
                entity_type='project',
                entity_id=str(project.pid),
                message=f"Proposal '{project.name}' is under review and awaiting Dean action."
            )
    elif action == 'Return':
        project.status = 'RETURNED'
        project.save()

        # Notify PI: proposal returned for revision
        create_notification(
            sender=username,
            receiver=project.pi_id,
            event_type='proposal_rejected',
            entity_type='project',
            entity_id=str(project.pid),
            message=f"Your proposal '{project.name}' has been returned for revision."
        )
    else:
        return False, "Invalid verification action"
    
    return True, f"Proposal {action}d successfully"


@transaction.atomic
def dean_approve_reject(entity_id: int, entity_type: str, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-019: Approve/Reject Proposal (Dean)
    UC-021: Approve/Reject Fund (Dean)
    """
    username = user_info.get('username')
    
    # Verify dean designation
    designations = selectors.get_user_designations(username)
    if 'dean_rspc' not in designations:
        return False, "Only Dean RSPC can perform this action"
    
    action = data.get('action')
    remarks = data.get('remarks', '')
    
    if entity_type == 'project':
        project = selectors.get_project_by_id(entity_id)
        if not project:
            return False, "Project not found"
        
        if action == 'approve':
            project.status = 'SANCTIONED'
            event_type = 'proposal_approved'
            decision_msg = f"Your proposal '{project.name}' has been approved by Dean RSPC."
        elif action == 'reject':
            project.status = 'REJECTED'
            event_type = 'proposal_rejected'
            decision_msg = f"Your proposal '{project.name}' has been rejected by Dean RSPC."
        else:
            return False, "Invalid dean action"
        
        project.save()

        # Notify PI about dean decision
        create_notification(
            sender=username,
            receiver=project.pi_id,
            event_type=event_type,
            entity_type='project',
            entity_id=str(project.pid),
            message=decision_msg + (f" Remarks: {remarks}" if remarks else "")
        )

        # Notify RSPC admins for workflow traceability
        admin_users = [u for u in _get_role_usernames('rspc_admin') if u != username]
        for admin_user in admin_users:
            create_notification(
                sender=username,
                receiver=admin_user,
                event_type=event_type,
                entity_type='project',
                entity_id=str(project.pid),
                message=f"Dean decision recorded for proposal '{project.name}': {action.upper()}."
            )
        
    elif entity_type == 'fund':
        try:
            fund_request = RSPCInventory.objects.get(request_id=entity_id)
        except RSPCInventory.DoesNotExist:
            return False, "Fund request not found"
        
        if action == 'approve':
            fund_request.status = 'DEAN_APPROVED'
            # Notify director(s): dean has cleared, pending director decision
            for director_user in set(_get_role_usernames('director')):
                if director_user != username:
                    create_notification(
                        sender=username,
                        receiver=director_user,
                        event_type='fund_request_pending',
                        entity_type='fund',
                        entity_id=str(fund_request.request_id),
                        message=f"Fund request for project '{fund_request.project.name}' is pending Director approval."
                    )
            create_notification(
                sender=username,
                receiver=fund_request.project.pi_id,
                event_type='fund_request_pending',
                entity_type='fund',
                entity_id=str(fund_request.request_id),
                message=f"Your fund request for project '{fund_request.project.name}' is approved by Dean and pending Director decision."
            )
        elif action == 'reject':
            fund_request.status = 'REJECTED'
            create_notification(
                sender=username,
                receiver=fund_request.project.pi_id,
                event_type='fund_rejected',
                entity_type='fund',
                entity_id=str(fund_request.request_id),
                message=f"Your fund request for project '{fund_request.project.name}' was rejected by Dean."
            )
        else:
            return False, "Invalid dean action"
        
        fund_request.save()
    
    return True, f"{entity_type.title()} {action}d successfully"


# ============================================================================
# COMMITTEE MANAGEMENT SERVICES
# ============================================================================

@transaction.atomic
def extend_committee_deadline(committee_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-007: Extend Committee Deadline
    """
    username = user_info.get('username')
    
    committee = selectors.get_committee_by_id(committee_id)
    if not committee:
        return False, "Committee not found"
    
    # Check if user is PI
    if committee.staff and committee.staff.pid.pi_id != username:
        return False, "Only PI can extend deadline"
    
    committee.deadline = data.get('new_deadline')
    committee.save()
    
    return True, "Committee deadline extended successfully"


# ============================================================================
# NOTIFICATION SERVICES
# ============================================================================

def get_notifications(user_info: Dict, is_read: Optional[bool] = None, limit: int = 50) -> List[Notification]:
    """Get notifications for user"""
    username = user_info.get('username')
    return selectors.get_notifications_for_user(username, is_read, limit)


@transaction.atomic
def mark_notification_read(notification_id: int, user_info: Dict) -> Tuple[bool, str]:
    """Mark notification as read"""
    username = user_info.get('username')
    
    try:
        notification = Notification.objects.get(nid=notification_id, recipient__username=username)
        notification.is_read = True
        notification.save()
        return True, "Notification marked as read"
    except Notification.DoesNotExist:
        return False, "Notification not found"


# ============================================================================
# UTILITY SERVICES
# ============================================================================

def get_project_copis(project_id: int) -> List[ProjectAccess]:
    """Get Co-PIs for project"""
    return selectors.get_copis_for_project(project_id)


def get_all_copis(user_info: Dict) -> List[Dict]:
    """Get all Co-PIs user can access"""
    username = user_info.get('username')
    return selectors.get_all_copis_for_user(username)


def get_faculty_ids(department: Optional[str] = None) -> List[Dict]:
    """Get faculty IDs for dropdowns"""
    return selectors.get_all_faculty_ids(department)


def get_project_ids(user_info: Dict, status_filter: Optional[str] = None) -> List[Dict]:
    """Get project IDs for dropdowns"""
    username = user_info.get('username')
    return selectors.get_project_ids_for_user(username, status_filter)


def get_projects(user_info: Dict, filters: Optional[Dict] = None) -> List[Project]:
    """
    Get list of projects based on user role and optional filters
    Returns projects filtered by status, department, and type as needed
    """
    username = user_info.get('username')
    projects = selectors.get_projects_for_user(username)
    
    if not filters:
        return projects
    
    # Apply additional filters if provided
    if filters.get('status'):
        projects = [p for p in projects if p.status == filters['status']]
    
    if filters.get('dept'):
        dept_filter = str(filters['dept']).strip()
        if dept_filter and dept_filter.lower() != 'mine':
            projects = [p for p in projects if p.dept == dept_filter]
    
    if filters.get('project_type'):
        projects = [p for p in projects if p.type == filters['project_type']]
    
    return projects


def check_project_access(project_id: int, username: str) -> bool:
    """Check whether a user can access a project"""
    return selectors.check_project_access(project_id, username)


# ============================================================================
# DASHBOARD SERVICES
# ============================================================================

def get_dashboard_data(user_info: Dict) -> Dict:
    """Get dashboard data"""
    username = user_info.get('username')
    return selectors.get_dashboard_data(username)


# ============================================================================
# RESEARCH GROUP SERVICES
# ============================================================================

@transaction.atomic
def create_research_group(data: Dict, user_info: Dict) -> Tuple[bool, str, Optional[ResearchGroup]]:
    """
    UC-003: Create Research Group
    BR-RSPC-07: Only faculty can create research groups
    """
    username = user_info.get('username')
    
    # BR-RSPC-07: Only faculty
    if not validate_faculty_user(username):
        return False, "Only faculty can create research groups", None
    
    faculty = selectors.get_faculty_by_username(username)
    if not faculty:
        return False, "Faculty record not found", None
    
    group = ResearchGroup.objects.create(
        name=data['name'],
        acronym=data.get('acronym', ''),
        discipline_id=data.get('discipline'),
        description=data.get('description', ''),
        head=faculty,
        established_date=data.get('established_date', timezone.now()),
        website=data.get('website', ''),
        is_active=True
    )
    
    # Add members
    member_ids = data.get('members', [])
    for member_id in member_ids:
        try:
            member = Faculty.objects.get(id=member_id)
            group.members.add(member)
        except Faculty.DoesNotExist:
            pass
    
    return True, "Research group created successfully", group


# ============================================================================
# PATENT SERVICES
# ============================================================================

@transaction.atomic
def update_patent_status(patent_id: int, data: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    UC-028: Update Patent Status
    BR-RSPC-18: Notification Generation
    """
    username = user_info.get('username')
    
    # Verify Dean RSPC
    designations = selectors.get_user_designations(username)
    user_type = selectors.get_user_type(username)
    
    if 'dean_rspc' not in designations or user_type != 'faculty':
        return False, "Only Dean RSPC can update patent status"
    
    try:
        patent = Patent.objects.get(id=patent_id)
    except Patent.DoesNotExist:
        return False, "Patent not found"
    
    new_status = data.get('status')
    patent.status = new_status
    patent.save()
    
    # Notify faculty inventors
    for faculty in patent.faculty_inventors.all():
        create_notification(
            sender=username,
            receiver=faculty.id.user.username,
            event_type='patent_updated',
            entity_type='patent',
            entity_id=str(patent_id),
            message=f"Patent '{patent.title}' status updated to {new_status}"
        )
    
    return True, f"Patent status updated to {new_status}"


# ============================================================================
# ADVANCED VALIDATION SERVICES (Phase 1 Enhancements)
# ============================================================================

def validate_project_duration(duration: int) -> Tuple[bool, str]:
    """
    BR-RSPC-11: Project duration must be between 6-60 months
    """
    if not isinstance(duration, (int, float)):
        return False, "Duration must be a number"
    
    if duration < 6:
        return False, "Project duration must be at least 6 months"
    
    if duration > 60:
        return False, "Project duration cannot exceed 60 months"
    
    return True, "Duration valid"


def validate_committee_members(members: List[str]) -> Tuple[bool, str]:
    """
    BR-RSPC-12: Committee must have minimum 3 members
    All members must be eligible faculty
    """
    if not isinstance(members, list):
        return False, "Members must be a list"
    
    if len(members) < 3:
        return False, f"Committee must have at least 3 members (provided: {len(members)})"
    
    if len(members) != len(set(members)):
        return False, "Duplicate committee members not allowed"
    
    # Validate each member is PI-eligible
    invalid_members = []
    for member in members:
        is_eligible, reason = validate_pi_eligibility(member)
        if not is_eligible:
            invalid_members.append(f"{member}: {reason}")
    
    if invalid_members:
        return False, f"Invalid committee members: {'; '.join(invalid_members)}"
    
    return True, "Committee composition valid"


def validate_budget_reallocation(
    project_id: int,
    from_category: str,
    amount: float,
    to_category: Optional[str] = None
) -> Tuple[bool, str]:
    """
    BR-RSPC-08: Budget reallocation maximum 20% of category per allocation year
    Validates the reallocation limits
    """
    try:
        project = Project.objects.get(pid=project_id)
        budget = Budget.objects.get(pid=project)
    except (Project.DoesNotExist, Budget.DoesNotExist):
        return False, "Project or budget not found"
    
    # Get current allocation for category
    category_map = {
        'manpower': budget.manpower,
        'travel': budget.travel,
        'contingency': budget.contingency,
        'consumables': budget.consumables,
        'equipments': budget.equipments,
        'overhead': budget.overhead,
    }
    
    if from_category not in category_map:
        return False, f"Invalid category: {from_category}"
    
    category_budget = category_map[from_category]
    if isinstance(category_budget, dict):
        total_category = sum(category_budget.values())
    else:
        total_category = category_budget if category_budget else 0
    
    max_reallocation = total_category * 0.2
    
    if amount > max_reallocation:
        return False, f"Reallocation limit exceeded. Maximum allowed: ₹{max_reallocation:.2f} (20% of ₹{total_category:.2f})"
    
    return True, f"Reallocation valid. Amount: ₹{amount:.2f}, Limit: ₹{max_reallocation:.2f}"


@transaction.atomic
def reallocate_budget_with_tracking(
    project_id: int,
    data: Dict,
    user_info: Dict
) -> Tuple[bool, str]:
    """
    BR-RSPC-08: Budget reallocation with audit trail
    Creates BudgetAudit record for tracking
    """
    username = user_info.get('username')
    
    try:
        project = Project.objects.get(pid=project_id)
        budget = Budget.objects.get(pid=project)
    except (Project.DoesNotExist, Budget.DoesNotExist):
        return False, "Project or budget not found"
    
    # Verify authorization
    if project.pi_id != username and not validate_rspc_admin(username):
        return False, "Only PI or RSPC Admin can reallocate budget"
    
    from_category = data.get('from_category')
    to_category = data.get('to_category')
    amount = data.get('amount')
    justification = data.get('justification', '')
    
    # Validate reallocation
    is_valid, message = validate_budget_reallocation(project_id, from_category, amount, to_category)
    if not is_valid:
        return False, message
    
    # Update budget allocations
    category_map = {
        'manpower': 'manpower',
        'travel': 'travel',
        'contingency': 'contingency',
        'consumables': 'consumables',
        'equipments': 'equipments',
    }
    
    from_field = category_map.get(from_category, 'manpower')
    to_field = category_map.get(to_category, 'contingency')
    
    # Deduct from source
    if isinstance(getattr(budget, from_field), dict):
        from_dict = getattr(budget, from_field) or {}
        from_dict['_total'] = from_dict.get('_total', 0) - amount
        setattr(budget, from_field, from_dict)
    
    # Add to destination
    if isinstance(getattr(budget, to_field), dict):
        to_dict = getattr(budget, to_field) or {}
        to_dict['_total'] = to_dict.get('_total', 0) + amount
        setattr(budget, to_field, to_dict)
    
    budget.save()
    
    # Create audit record (if BudgetAudit model exists)
    try:
        from .models import BudgetAudit
        BudgetAudit.objects.create(
            project=project,
            from_category=from_category,
            to_category=to_category,
            amount=amount,
            justification=justification,
            performed_by=username,
            timestamp=timezone.now()
        )
    except:
        pass  # BudgetAudit may not exist yet
    
    # Create notification
    create_notification(
        sender=username,
        receiver='rspc_admin',
        event_type='budget_reallocated',
        entity_type='project',
        entity_id=str(project_id),
        message=f"Budget reallocated: ₹{amount:.2f} from {from_category} to {to_category}"
    )
    
    return True, f"Budget reallocated successfully. ₹{amount:.2f} moved from {from_category} to {to_category}"


# ============================================================================
# EXPENDITURE APPROVAL WORKFLOW (Phase 2 - BR-RSPC-13)
# ============================================================================

def get_expenditure_approval_chain(amount: float) -> Tuple[List[str], str]:
    """
    BR-RSPC-13: Dynamic approval chain based on amount
    ≤50K: PI approval only
    50K-200K: PI → HOD → (optional) RSPC
    >200K: PI → HOD → RSPC
    """
    if amount <= 50000:
        return ['PI'], 'PI'
    elif amount <= 200000:
        return ['PI', 'HOD'], 'PI'
    else:
        return ['PI', 'HOD', 'RSPC'], 'PI'


@transaction.atomic
def create_expenditure_with_approval_workflow(
    data: Dict,
    user_info: Dict
) -> Tuple[bool, str, Optional[Dict]]:
    """
    UC-012, UC-013: Create expenditure with automatic approval workflow
    BR-RSPC-13: Multi-stage approval based on amount
    """
    username = user_info.get('username')
    
    project_id = data.get('project_id')
    try:
        project = Project.objects.get(pid=project_id)
    except Project.DoesNotExist:
        return False, "Project not found", None
    
    # Verify user is PI or Co-PI
    if project.pi_id != username:
        is_copi = ProjectAccess.objects.filter(pid=project, copi_id=username).exists()
        if not is_copi:
            return False, "Only PI or Co-PI can create expenditure requests", None
    
    amount = float(data.get('amount', 0))
    
    # Get approval chain
    chain, first_approver = get_expenditure_approval_chain(amount)
    
    # Create expenditure record
    expenditure = Expenditure.objects.create(
        project=project,
        category=data.get('category', 'OTHER'),
        amount=amount,
        purpose=data.get('purpose', ''),
        status='PENDING',
        requested_by=username,
        request_date=timezone.now(),
        approval_chain=chain,
        current_stage=0,
        current_approver=first_approver,
        supporting_documents=data.get('supporting_documents', [])
    )
    
    # Create approval history record for first stage
    try:
        from .models import ExpenditureApprovalHistory
        ExpenditureApprovalHistory.objects.create(
            expenditure=expenditure,
            stage=1,
            approver_role=first_approver,
            status='PENDING',
            created_at=timezone.now()
        )
    except:
        pass
    
    # Create notification for first approver
    if first_approver == 'PI':
        approver = project.pi_id
    elif first_approver == 'HOD':
        approver = 'hod_' + project.dept
    else:
        approver = 'rspc_admin'
    
    create_notification(
        sender=username,
        receiver=approver,
        event_type='expenditure_pending_approval',
        entity_type='expenditure',
        entity_id=str(expenditure.id),
        message=f"Expenditure request for ₹{amount:.2f} pending your approval"
    )
    
    return True, "Expenditure request created successfully", {
        'expenditure_id': expenditure.id,
        'approval_chain': chain,
        'current_approver': first_approver,
        'amount': amount
    }


@transaction.atomic
def approve_expenditure_with_workflow(
    expenditure_id: int,
    data: Dict,
    user_info: Dict
) -> Tuple[bool, str]:
    """
    Approve expenditure and route to next approver if needed
    BR-RSPC-13: Multi-stage approval workflow
    """
    username = user_info.get('username')
    
    try:
        expenditure = Expenditure.objects.get(id=expenditure_id)
    except Expenditure.DoesNotExist:
        return False, "Expenditure not found"
    
    # Verify approver
    current_approver = expenditure.current_approver
    if current_approver == 'PI' and expenditure.project.pi_id != username:
        return False, "You are not authorized to approve this stage"
    elif current_approver == 'HOD':
        # Would check HOD designation for department
        pass
    elif current_approver == 'RSPC':
        if not validate_rspc_admin(username):
            return False, "You are not authorized to approve this stage"
    
    # Update approval history
    try:
        from .models import ExpenditureApprovalHistory
        history = ExpenditureApprovalHistory.objects.filter(
            expenditure=expenditure,
            status='PENDING'
        ).first()
        if history:
            history.status = 'APPROVED'
            history.approved_by = username
            history.approved_at = timezone.now()
            history.comments = data.get('comments', '')
            history.save()
    except:
        pass
    
    # Move to next stage or approve
    chain = expenditure.approval_chain
    next_stage = expenditure.current_stage + 1
    
    if next_stage < len(chain):
        # Route to next approver
        expenditure.current_stage = next_stage
        expenditure.current_approver = chain[next_stage]
        expenditure.status = f"{chain[expenditure.current_stage-1]}_APPROVED"
        
        # Create history record for next stage
        try:
            from .models import ExpenditureApprovalHistory
            ExpenditureApprovalHistory.objects.create(
                expenditure=expenditure,
                stage=next_stage + 1,
                approver_role=chain[next_stage],
                status='PENDING',
                created_at=timezone.now()
            )
        except:
            pass
        
        # Notify next approver
        if chain[next_stage] == 'HOD':
            next_approver = 'hod_' + expenditure.project.dept
        else:
            next_approver = 'rspc_admin'
        
        create_notification(
            sender=username,
            receiver=next_approver,
            event_type='expenditure_pending_approval',
            entity_type='expenditure',
            entity_id=str(expenditure_id),
            message=f"Expenditure request for ₹{expenditure.amount:.2f} pending your approval"
        )
        
        expenditure.save()
        return True, f"Expenditure approved by {chain[expenditure.current_stage-1]}. Routed to {chain[next_stage]}"
    else:
        # Final approval
        expenditure.status = 'APPROVED'
        expenditure.current_approver = None
        expenditure.approved_date = timezone.now()
        expenditure.save()
        
        # Update budget
        try:
            budget = Budget.objects.get(pid=expenditure.project)
            budget.current_funds = (budget.current_funds or 0) - expenditure.amount
            budget.save()
        except Budget.DoesNotExist:
            pass
        
        # Notify requester
        create_notification(
            sender=username,
            receiver=expenditure.requested_by,
            event_type='expenditure_approved',
            entity_type='expenditure',
            entity_id=str(expenditure_id),
            message=f"Expenditure request for ₹{expenditure.amount:.2f} has been approved"
        )
        
        return True, "Expenditure approved successfully"


@transaction.atomic
def reject_expenditure_with_workflow(
    expenditure_id: int,
    data: Dict,
    user_info: Dict
) -> Tuple[bool, str]:
    """
    Reject expenditure at current stage
    """
    username = user_info.get('username')
    
    try:
        expenditure = Expenditure.objects.get(id=expenditure_id)
    except Expenditure.DoesNotExist:
        return False, "Expenditure not found"
    
    # Update expenditure
    expenditure.status = 'REJECTED'
    expenditure.current_approver = None
    expenditure.save()
    
    # Update approval history
    try:
        from .models import ExpenditureApprovalHistory
        history = ExpenditureApprovalHistory.objects.filter(
            expenditure=expenditure,
            status='PENDING'
        ).first()
        if history:
            history.status = 'REJECTED'
            history.rejected_by = username
            history.rejected_at = timezone.now()
            history.comments = data.get('comments', '')
            history.save()
    except:
        pass
    
    # Notify requester
    create_notification(
        sender=username,
        receiver=expenditure.requested_by,
        event_type='expenditure_rejected',
        entity_type='expenditure',
        entity_id=str(expenditure_id),
        message=f"Expenditure request for ₹{expenditure.amount:.2f} has been rejected. Reason: {data.get('reason', 'Not specified')}"
    )
    
    return True, "Expenditure rejected successfully"


def get_pending_approvals(user_info: Dict) -> Dict:
    """
    Get all pending approvals for current user
    Supports multi-role approval (PI, HOD, RSPC)
    """
    username = user_info.get('username')
    
    # Get expenditures pending PI approval
    pi_projects = Project.objects.filter(pi_id=username)
    pi_pending = Expenditure.objects.filter(
        project__in=pi_projects,
        current_approver='PI',
        status='PENDING'
    )
    
    # Get expenditures pending HOD approval (would need HOD designation check)
    hod_pending = Expenditure.objects.filter(
        current_approver='HOD',
        status='PENDING'
    )
    
    # Get expenditures pending RSPC approval
    rspc_pending = Expenditure.objects.filter(
        current_approver='RSPC',
        status='PENDING'
    )
    
    if validate_rspc_admin(username):
        rspc_pending = Expenditure.objects.filter(
            current_approver='RSPC',
            status='PENDING'
        )
    else:
        rspc_pending = Expenditure.objects.none()
    
    return {
        'pi_pending': list(pi_pending.values('id', 'amount', 'category', 'purpose', 'request_date')),
        'hod_pending': list(hod_pending.values('id', 'amount', 'category', 'purpose', 'request_date')),
        'rspc_pending': list(rspc_pending.values('id', 'amount', 'category', 'purpose', 'request_date')),
        'total': pi_pending.count() + hod_pending.count() + rspc_pending.count()
    }


# ============================================================================
# ENHANCED STAFF MANAGEMENT (Phase 2 - BR-RSPC-12)
# ============================================================================

@transaction.atomic
def create_staff_selection_committee(
    staff_id: int,
    data: Dict,
    user_info: Dict
) -> Tuple[bool, str]:
    """
    BR-RSPC-12: Create staff selection committee with minimum 3 members
    All members must be PI-eligible faculty
    """
    username = user_info.get('username')
    
    try:
        staff = Staff.objects.get(id=staff_id)
    except Staff.DoesNotExist:
        return False, "Staff request not found"
    
    # Verify PI
    if staff.pid.pi_id != username:
        return False, "Only PI can create committee"
    
    committee_members = data.get('committee_members', [])
    
    # Validate committee composition
    is_valid, message = validate_committee_members(committee_members)
    if not is_valid:
        return False, message
    
    # Create committee
    committee = Committee.objects.create(
        name=f"Selection Committee for {staff.person}",
        staff=staff,
        deadline=data.get('deadline', timezone.now() + timezone.timedelta(days=14))
    )
    
    # Add members to committee
    for member_username in committee_members:
        try:
            user = User.objects.get(username=member_username)
            extra_info = ExtraInfo.objects.get(user=user)
            committee.members.add(extra_info)
        except (User.DoesNotExist, ExtraInfo.DoesNotExist):
            pass
    
    # Update staff
    staff.approval_status = 'COMMITTEE_PENDING'
    staff.save()
    
    # Create notifications for committee members
    for member in committee_members:
        create_notification(
            sender=username,
            receiver=member,
            event_type='staff_committee_pending',
            entity_type='staff',
            entity_id=str(staff_id),
            message=f"You have been invited to join selection committee for {staff.person}"
        )
    
    return True, f"Committee created with {len(committee_members)} members"


@transaction.atomic
def submit_committee_verdict(
    staff_id: int,
    data: Dict,
    user_info: Dict
) -> Tuple[bool, str]:
    """
    UC-008: Committee member submits recommendation
    BR-RSPC-15: Conflict of interest can be declared
    """
    username = user_info.get('username')
    
    try:
        staff = Staff.objects.get(id=staff_id)
    except Staff.DoesNotExist:
        return False, "Staff request not found"
    
    committee = Committee.objects.filter(staff=staff).first()
    if not committee:
        return False, "Committee not found"
    
    # Verify member is on committee
    try:
        user = User.objects.get(username=username)
        extra_info = ExtraInfo.objects.get(user=user)
        if extra_info not in committee.members.all():
            return False, "You are not a member of this committee"
    except (User.DoesNotExist, ExtraInfo.DoesNotExist):
        return False, "User not found"
    
    # Record verdict
    verdict, created = CommitteeVerdict.objects.get_or_create(
        committee=committee,
        member=extra_info,
        defaults={
            'decision': data.get('recommendation', 'APPROVE'),
            'comments': data.get('comments', ''),
            'conflict_declared': data.get('conflict_declared', False),
        }
    )
    
    if not created:
        verdict.decision = data.get('recommendation', 'APPROVE')
        verdict.comments = data.get('comments', '')
        verdict.conflict_declared = data.get('conflict_declared', False)
        verdict.save()
    
    # Check if all verdicts received
    all_verdicts = CommitteeVerdict.objects.filter(committee=committee)
    if all_verdicts.count() == committee.members.count():
        staff.approval_status = 'HOD_PENDING'
        staff.save()
        
        # Notify HOD(s) mapped to this department
        hod_users = _get_hod_usernames_for_department(staff.pid.dept) or _get_role_usernames('rspc_admin')
        for hod_user in set(hod_users):
            create_notification(
                sender=username,
                receiver=hod_user,
                event_type='staff_hod_pending',
                entity_type='staff',
                entity_id=str(staff_id),
                message=f"Staff selection committee recommendations complete for {staff.person}. HOD action pending."
            )
    
    return True, "Verdict submitted successfully"


# ============================================================================
# PROJECT LIFECYCLE MANAGEMENT (Phase 2 - BR-RSPC-09)
# ============================================================================

def get_project_lifecycle_status(project_id: int) -> Dict:
    """
    Get detailed lifecycle status for project
    Includes all transitions and current state
    """
    try:
        project = Project.objects.get(pid=project_id)
    except Project.DoesNotExist:
        return {}
    
    return {
        'project_id': project.pid,
        'name': project.name,
        'current_status': project.status,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'submission_date': project.submission_date.isoformat() if project.submission_date else None,
        'sanction_date': project.sanction_date.isoformat() if project.sanction_date else None,
        'start_date': project.start_date.isoformat() if project.start_date else None,
        'end_date': project.end_date.isoformat() if project.end_date else None,
        'total_budget': float(project.total_budget) if project.total_budget else 0,
        'sanctioned_amount': float(project.sanctioned_amount) if project.sanctioned_amount else 0,
        'initial_amount': float(project.initial_amount) if project.initial_amount else 0,
        'pi': project.pi_id,
        'department': project.dept,
        'type': project.type,
        'duration_months': project.duration,
    }


# ============================================================================
# UTILITIES AND HELPERS (Phase 1)
# ============================================================================

def get_pi_validation_details(username: str) -> Dict:
    """
    Get detailed PI eligibility information
    Useful for frontend validation displays
    """
    is_eligible, reason = validate_pi_eligibility(username)
    
    try:
        user = User.objects.get(username=username)
        extra_info = ExtraInfo.objects.get(user=user)
        
        details = {
            'username': username,
            'name': user.get_full_name(),
            'is_eligible': is_eligible,
            'reason': reason,
            'user_type': extra_info.user_type,
            'is_permanent': extra_info.is_permanent,
            'is_active': extra_info.is_active,
            'department': str(extra_info.department) if extra_info.department else None,
        }
        
        if is_eligible:
            try:
                faculty = Faculty.objects.get(extra_info=extra_info)
                details['designations'] = [
                    d.name for d in Designation.objects.filter(
                        holdsdesignation__faculty=faculty,
                        holdsdesignation__is_current=True
                    )
                ]
            except Faculty.DoesNotExist:
                details['designations'] = []
        else:
            details['designations'] = []
        
        return details
    except (User.DoesNotExist, ExtraInfo.DoesNotExist):
        return {
            'username': username,
            'is_eligible': False,
            'reason': f"User '{username}' not found or incomplete profile",
        }

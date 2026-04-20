"""
Staff Management Workflow Services (UC-007, UC-008, UC-026, UC-027)
Comprehensive business logic for staff approval workflow with 7 stages

Workflow: DRAFT → COMMITTEE_PENDING → COMMITTEE_APPROVED → HOD_PENDING → 
          HOD_APPROVED → RSPC_PENDING → APPOINTED
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from applications.globals.models import ExtraInfo, HoldsDesignation, Designation
from .models import (
    Staff, Committee, CommitteeVerdict, CommitteeMember, CommitteeDecision,
    Project, StaffAllocation, StaffApprovalStatus, Notification, StaffType
)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class StaffWorkflowError(Exception):
    """Base exception for staff workflow operations"""
    pass


class ConflictOfInterestError(StaffWorkflowError):
    """Raised when member has declared conflict of interest (BR-RSPC-15)"""
    pass


# ============================================================================
# STAFF REQUEST SERVICE (UC-007)
# ============================================================================

@transaction.atomic
def create_staff_request(
    project_id: int,
    data: Dict[str, Any],
    user: User
) -> Tuple[bool, str, Optional[Staff]]:
    """
    UC-007: Create staff request (DRAFT stage)
    
    Args:
        project_id: Project ID
        data: Staff request data
        user: Current user (must be PI)
    
    Returns:
        (success, message, staff_object)
    
    Validates:
        - User is PI of the project
        - Qualification and experience requirements
        - Number of positions > 0
    """
    try:
        # Verify user is PI
        project = Project.objects.get(pid=project_id)
        
        try:
            pi_info = ExtraInfo.objects.get(user__username=project.pi_id)
        except ExtraInfo.DoesNotExist:
            return False, f"Project PI '{project.pi_id}' not found", None
        
        if user.username != project.pi_id:
            return False, "Only project PI can request staff", None
        
        # Validate request data
        position_type = data.get('type', '')
        if position_type not in dict(StaffType.choices):
            return False, f"Invalid position type: {position_type}", None
        
        no_of_positions = data.get('no_of_positions', 1)
        if no_of_positions < 1:
            return False, "Number of positions must be at least 1", None
        
        experience = data.get('experience', 0)
        if experience < 0:
            return False, "Experience cannot be negative", None
        
        # Create staff request
        staff = Staff.objects.create(
            pid=project,
            person=data.get('person', ''),
            uname=data.get('uname', ''),
            biodata_number=data.get('biodata_number', ''),
            type=position_type,
            salary=data.get('salary', 0),
            has_funds=data.get('has_funds', False),
            post_on_website=data.get('post_on_website', False),
            eligibility=data.get('eligibility', ''),
            start_date=data.get('start_date'),
            duration=data.get('duration', 12),
            approval_status=StaffApprovalStatus.DRAFT,
            created_by=user,
            no_of_positions=no_of_positions,
            qualification=data.get('qualification', ''),
            experience=experience,
            approval_chain={}
        )
        
        return True, "Staff request created successfully", staff
        
    except Project.DoesNotExist:
        return False, f"Project {project_id} not found", None
    except Exception as e:
        return False, f"Error creating staff request: {str(e)}", None


# ============================================================================
# COMMITTEE CREATION SERVICE (UC-026, BR-RSPC-12)
# ============================================================================

@transaction.atomic
def create_staff_committee(
    staff_id: int,
    member_ids: List[int],
    deadline: datetime,
    committee_name: str = "Staff Selection Committee",
    user: Optional[User] = None
) -> Tuple[bool, str, Optional[Committee]]:
    """
    UC-026: Create committee for staff selection (BR-RSPC-12)
    
    Enforces:
        - Minimum 3 members (BR-RSPC-12)
        - All members must be PI-eligible (Professor/Assoc/Asst Prof)
        - All members must be valid users
    
    Args:
        staff_id: Staff ID
        member_ids: List of ExtraInfo IDs for committee members
        deadline: Committee deadline
        committee_name: Name of committee
        user: Current user (optional, for authorization)
    
    Returns:
        (success, message, committee_object)
    """
    try:
        # Verify staff exists
        staff = Staff.objects.get(sid=staff_id)
        
        # BR-RSPC-12: Validate minimum 3 members
        if len(member_ids) < 3:
            return False, "BR-RSPC-12: Committee must have at least 3 members", None
        
        # Verify all members exist and are PI-eligible
        PI_ELIGIBLE_DESIGNATIONS = [
            'Professor', 'Associate Professor', 'Assistant Professor',
            'Assoc. Prof', 'Asst. Prof', 'Prof', 'Assoc Prof'
        ]
        
        members = []
        non_eligible = []
        
        for member_id in member_ids:
            try:
                extra_info = ExtraInfo.objects.get(id=member_id)
                members.append(extra_info)
                
                # Check PI eligibility
                designations = HoldsDesignation.objects.filter(
                    extra_info=extra_info
                ).values_list('designation__designation_name', flat=True)
                
                is_pi_eligible = any(d in PI_ELIGIBLE_DESIGNATIONS for d in designations)
                
                if not is_pi_eligible:
                    non_eligible.append(member_id)
                    
            except ExtraInfo.DoesNotExist:
                return False, f"Committee member {member_id} not found", None
        
        if non_eligible:
            return False, (
                f"BR-RSPC-12: Members {non_eligible} are not PI-eligible "
                "(must be Professor/Assoc/Asst Prof)"
            ), None
        
        # Validate deadline
        if deadline <= timezone.now():
            return False, "Committee deadline must be in the future", None
        
        # Create or update committee
        committee, created = Committee.objects.update_or_create(
            staff=staff,
            defaults={
                'name': committee_name,
                'deadline': deadline,
            }
        )
        
        # Clear existing members and add new ones
        committee.members.clear()
        committee.members.add(*members)
        
        # Create CommitteeMember records with PI eligibility tracking
        for extra_info in members:
            CommitteeMember.objects.update_or_create(
                committee=committee,
                member=extra_info,
                defaults={
                    'is_pi_eligible': True,
                    'designation': extra_info.user.get_full_name() if extra_info.user else '',
                    'department': str(extra_info.department) if extra_info.department else '',
                }
            )
        
        # Transition staff status
        staff.approval_status = StaffApprovalStatus.COMMITTEE_PENDING
        staff.approval_chain = {
            'committee_created': {
                'timestamp': timezone.now().isoformat(),
                'members': member_ids,
                'deadline': deadline.isoformat()
            }
        }
        staff.save()
        
        return True, "Committee created successfully (BR-RSPC-12 validated)", committee
        
    except Staff.DoesNotExist:
        return False, f"Staff {staff_id} not found", None
    except Exception as e:
        return False, f"Error creating committee: {str(e)}", None


# ============================================================================
# COMMITTEE VERDICT SERVICE (UC-008, BR-RSPC-15)
# ============================================================================

@transaction.atomic
def submit_committee_verdict(
    staff_id: int,
    committee_member_id: int,
    decision: Optional[str],
    comments: str = "",
    has_conflict: bool = False,
    conflict_reason: str = "",
    user: Optional[User] = None
) -> Tuple[bool, str]:
    """
    UC-008: Submit committee verdict (BR-RSPC-15 conflict of interest)
    
    Enforces:
        - Member must be in the committee
        - Cannot submit verdict if conflict of interest (BR-RSPC-15)
        - All verdicts must be submitted before approval
        - Valid decisions: APPROVE, REJECT, ABSTAIN
    
    Args:
        staff_id: Staff ID
        committee_member_id: ExtraInfo ID of committee member
        decision: APPROVE/REJECT/ABSTAIN or None if conflict
        comments: Verdict comments
        has_conflict: Whether member has conflict of interest
        conflict_reason: Reason for conflict if applicable
        user: Current user (optional, for authorization)
    
    Returns:
        (success, message)
    """
    try:
        staff = Staff.objects.get(sid=staff_id)
        committee = staff.get_committee()
        
        if not committee:
            return False, "No committee assigned to this staff request"
        
        # Verify member is in committee
        try:
            member = ExtraInfo.objects.get(id=committee_member_id)
        except ExtraInfo.DoesNotExist:
            return False, f"Committee member {committee_member_id} not found"
        
        if not committee.members.filter(id=committee_member_id).exists():
            return False, "Member is not part of this committee"
        
        # BR-RSPC-15: Handle conflict of interest
        if has_conflict:
            if not conflict_reason:
                return False, "Conflict reason must be provided (BR-RSPC-15)"
            
            # Cannot submit verdict if conflict exists
            decision = None
        
        # Validate decision if no conflict
        if not has_conflict and decision:
            if decision not in [CommitteeDecision.APPROVE, CommitteeDecision.REJECT, CommitteeDecision.ABSTAIN]:
                return False, f"Invalid decision: {decision}"
        
        # Create or update verdict
        verdict, created = CommitteeVerdict.objects.update_or_create(
            committee=committee,
            member=member,
            defaults={
                'decision': decision if not has_conflict else None,
                'comments': comments,
                'has_conflict_of_interest': has_conflict,
                'conflict_reason': conflict_reason,
                'submitted_date': timezone.now(),
            }
        )
        
        # Check if all verdicts submitted (excluding conflicts)
        total_members = committee.members.count()
        submitted_verdicts = CommitteeVerdict.objects.filter(
            committee=committee,
            decision__isnull=False
        ).count()
        
        # Auto-transition if all verdicts submitted
        if submitted_verdicts == total_members:
            # Check if any rejection
            rejections = CommitteeVerdict.objects.filter(
                committee=committee,
                decision=CommitteeDecision.REJECT
            ).count()
            
            if rejections > 0:
                staff.approval_status = StaffApprovalStatus.COMMITTEE_REJECTED
            else:
                staff.approval_status = StaffApprovalStatus.COMMITTEE_APPROVED
            
            staff.approval_chain = {
                **staff.approval_chain,
                'committee_verdicts': {
                    'timestamp': timezone.now().isoformat(),
                    'total_approved': total_members - rejections,
                    'total_rejected': rejections,
                }
            }
            staff.save()
        
        return True, f"Verdict submitted successfully {'(Conflict noted)' if has_conflict else ''}"
        
    except Staff.DoesNotExist:
        return False, f"Staff {staff_id} not found"
    except Exception as e:
        return False, f"Error submitting verdict: {str(e)}"


# ============================================================================
# WORKFLOW TRANSITION SERVICE
# ============================================================================

@transaction.atomic
def transition_staff_status(
    staff_id: int,
    new_status: str,
    approver_username: str = "",
    comments: str = ""
) -> Tuple[bool, str]:
    """
    Universal workflow transition with validation
    
    Args:
        staff_id: Staff ID
        new_status: Target status
        approver_username: User making the transition
        comments: Approval/rejection comments
    
    Returns:
        (success, message)
    """
    try:
        staff = Staff.objects.get(sid=staff_id)
        
        # Validate transition
        can_transition, reason = staff.can_transition_to(new_status)
        if not can_transition:
            return False, reason
        
        # Store transition in approval chain
        stage = new_status.lower()
        staff.approval_chain = {
            **staff.approval_chain,
            stage: {
                'timestamp': timezone.now().isoformat(),
                'approver': approver_username,
                'comments': comments,
            }
        }
        
        # Update status
        staff.approval_status = new_status
        staff.save()
        
        return True, f"Status transitioned to {new_status}"
        
    except Staff.DoesNotExist:
        return False, f"Staff {staff_id} not found"
    except Exception as e:
        return False, f"Error transitioning status: {str(e)}"


# ============================================================================
# HOD APPROVAL SERVICE
# ============================================================================

@transaction.atomic
def hod_approve_staff(
    staff_id: int,
    action: str,  # 'APPROVE' or 'REJECT'
    comments: str = "",
    user: Optional[User] = None
) -> Tuple[bool, str]:
    """
    HOD approval/rejection (HOD_PENDING → HOD_APPROVED/HOD_REJECTED)
    
    Args:
        staff_id: Staff ID
        action: APPROVE or REJECT
        comments: HOD comments
        user: Current user (HOD)
    
    Returns:
        (success, message)
    """
    try:
        staff = Staff.objects.get(sid=staff_id)
        
        if staff.approval_status != StaffApprovalStatus.HOD_PENDING:
            return False, f"Staff is not in HOD_PENDING status (current: {staff.approval_status})"
        
        if action == 'APPROVE':
            new_status = StaffApprovalStatus.HOD_APPROVED
            next_stage = StaffApprovalStatus.RSPC_PENDING
        elif action == 'REJECT':
            new_status = StaffApprovalStatus.HOD_REJECTED
            next_stage = StaffApprovalStatus.REJECTED
        else:
            return False, "Action must be APPROVE or REJECT"
        
        staff.approval_status = new_status
        staff.current_approver = user.username if user else ""
        
        # Update approval chain
        staff.approval_chain = {
            **staff.approval_chain,
            'hod_review': {
                'timestamp': timezone.now().isoformat(),
                'action': action,
                'approver': user.username if user else "",
                'comments': comments,
            }
        }
        
        if action == 'APPROVE':
            staff.approval_status = next_stage
        
        staff.save()
        
        return True, f"HOD {action} recorded successfully"
        
    except Staff.DoesNotExist:
        return False, f"Staff {staff_id} not found"
    except Exception as e:
        return False, f"Error recording HOD approval: {str(e)}"


# ============================================================================
# RSPC ADMIN APPROVAL SERVICE
# ============================================================================

@transaction.atomic
def rspc_approve_staff(
    staff_id: int,
    action: str,  # 'APPROVE' or 'REJECT'
    comments: str = "",
    user: Optional[User] = None
) -> Tuple[bool, str]:
    """
    RSPC Admin final approval (RSPC_PENDING → APPOINTED/RSPC_REJECTED)
    
    Creates StaffAllocation record on appointment
    
    Args:
        staff_id: Staff ID
        action: APPROVE or REJECT
        comments: RSPC comments
        user: Current user (RSPC Admin)
    
    Returns:
        (success, message)
    """
    try:
        staff = Staff.objects.get(sid=staff_id)
        
        if staff.approval_status != StaffApprovalStatus.RSPC_PENDING:
            return False, f"Staff is not in RSPC_PENDING status (current: {staff.approval_status})"
        
        if action == 'APPROVE':
            new_status = StaffApprovalStatus.APPOINTED
        elif action == 'REJECT':
            new_status = StaffApprovalStatus.RSPC_REJECTED
        else:
            return False, "Action must be APPROVE or REJECT"
        
        staff.approval_status = new_status
        staff.current_approver = user.username if user else ""
        staff.doc_approval = True if action == 'APPROVE' else False
        
        # Update approval chain
        staff.approval_chain = {
            **staff.approval_chain,
            'rspc_review': {
                'timestamp': timezone.now().isoformat(),
                'action': action,
                'approver': user.username if user else "",
                'comments': comments,
            }
        }
        
        # Create StaffAllocation if approved
        if action == 'APPROVE':
            StaffAllocation.objects.create(
                project=staff.pid,
                staff_id=staff.uname,
                name=staff.person,
                qualification=staff.qualification,
                stipend=staff.salary_per_month or staff.salary,
                year=timezone.now().year,
                start_date=staff.start_date.date() if staff.start_date else timezone.now().date(),
                end_date=(staff.start_date + timezone.timedelta(days=staff.duration * 30)).date() if staff.start_date else None
            )
        
        staff.save()
        
        return True, f"RSPC Admin {action} recorded. Staff {'APPOINTED' if action == 'APPROVE' else 'REJECTED'}"
        
    except Staff.DoesNotExist:
        return False, f"Staff {staff_id} not found"
    except Exception as e:
        return False, f"Error recording RSPC approval: {str(e)}"


# ============================================================================
# SELECTION REPORT SERVICE (UC-027)
# ============================================================================

@transaction.atomic
def generate_selection_report(
    staff_id: int,
    selected_candidates: List[Dict],
    user: Optional[User] = None
) -> Tuple[bool, str]:
    """
    UC-027: Generate final selection report
    
    Args:
        staff_id: Staff ID
        selected_candidates: List of selected candidate details
        user: Current user (PI)
    
    Returns:
        (success, message)
    """
    try:
        staff = Staff.objects.get(sid=staff_id)
        
        # Validate selected candidates
        required_fields = ['name', 'designation', 'offer_date', 'stipend']
        for idx, candidate in enumerate(selected_candidates):
            missing = [f for f in required_fields if f not in candidate]
            if missing:
                return False, f"Candidate {idx} missing fields: {missing}"
        
        # Update staff with selection
        staff.final_selection = selected_candidates
        staff.approval_status = StaffApprovalStatus.HOD_PENDING
        staff.submission_date = timezone.now()
        
        staff.approval_chain = {
            **staff.approval_chain,
            'selection_report': {
                'timestamp': timezone.now().isoformat(),
                'submitted_by': user.username if user else "",
                'candidates_selected': len(selected_candidates),
            }
        }
        
        staff.save()
        
        return True, f"Selection report submitted. {len(selected_candidates)} candidates selected"
        
    except Staff.DoesNotExist:
        return False, f"Staff {staff_id} not found"
    except Exception as e:
        return False, f"Error generating selection report: {str(e)}"


# ============================================================================
# WORKFLOW STATUS HELPER
# ============================================================================

def get_staff_workflow_status(staff_id: int) -> Dict[str, Any]:
    """
    Get current workflow status and next steps
    
    Returns dict with:
        - current_stage
        - stage_display
        - next_step
        - approval_chain
        - can_submit (bool)
    """
    try:
        staff = Staff.objects.get(sid=staff_id)
        
        stage_map = {
            StaffApprovalStatus.DRAFT: "Draft - PI Created",
            StaffApprovalStatus.COMMITTEE_PENDING: "Committee - Pending Verdicts",
            StaffApprovalStatus.COMMITTEE_APPROVED: "Committee - Approved",
            StaffApprovalStatus.COMMITTEE_REJECTED: "Committee - Rejected",
            StaffApprovalStatus.HOD_PENDING: "HOD - Pending Review",
            StaffApprovalStatus.HOD_APPROVED: "HOD - Approved",
            StaffApprovalStatus.HOD_REJECTED: "HOD - Rejected",
            StaffApprovalStatus.RSPC_PENDING: "RSPC Admin - Pending Review",
            StaffApprovalStatus.RSPC_APPROVED: "RSPC Admin - Approved",
            StaffApprovalStatus.RSPC_REJECTED: "RSPC Admin - Rejected",
            StaffApprovalStatus.APPOINTED: "Appointed - Complete",
            StaffApprovalStatus.REJECTED: "Rejected - Closed",
        }
        
        next_steps = {
            StaffApprovalStatus.DRAFT: "Create committee with 3+ PI-eligible members",
            StaffApprovalStatus.COMMITTEE_PENDING: "Await committee member verdicts",
            StaffApprovalStatus.COMMITTEE_APPROVED: "Route to HOD for review",
            StaffApprovalStatus.HOD_PENDING: "Await HOD approval/rejection",
            StaffApprovalStatus.HOD_APPROVED: "Route to RSPC Admin for final approval",
            StaffApprovalStatus.RSPC_PENDING: "Await RSPC Admin final decision",
            StaffApprovalStatus.RSPC_APPROVED: "Staff appointment complete",
            StaffApprovalStatus.APPOINTED: "No further action required",
        }
        
        return {
            'current_stage': staff.approval_status,
            'stage_display': stage_map.get(staff.approval_status, staff.approval_status),
            'next_step': next_steps.get(staff.approval_status, "Unknown"),
            'approval_chain': staff.approval_chain,
            'can_submit': staff.approval_status == StaffApprovalStatus.DRAFT,
            'current_approver': staff.current_approver or 'Pending',
            'submission_date': staff.submission_date.isoformat() if staff.submission_date else None,
        }
        
    except Staff.DoesNotExist:
        return {'error': f'Staff {staff_id} not found'}

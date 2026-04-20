"""
RSPC Module - Project Management Services
UC-004, UC-005, UC-012, UC-013 implementations

Handles:
- Project versioning and update tracking
- Project cancellation workflow
- Proposal vetting (HOD role)
- Department project management
"""

from django.db import transaction
from django.db.models import Sum, Case, When, DecimalField
from django.utils import timezone
from django.contrib.auth.models import User
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from applications.globals.models import Faculty, HoldsDesignation, ExtraInfo
from .models import (
    Project, ProjectVersion, CancellationRequest, ProposalVetting,
    Staff, Notification, ChangeType, ProjectStatus
)


# ============================================================================
# UC-004: PROJECT VERSION & UPDATE SERVICES
# ============================================================================

class ProjectVersionService:
    """
    Handles project updates and version tracking (UC-004)
    BR-011: No updates after approval (unless explicitly allowed)
    """
    
    @staticmethod
    def can_update_project(project: Project, user: User) -> Tuple[bool, str]:
        """
        Check if project can be updated
        BR-011: Only if SUBMITTED or if allow_updates_after_approval=True
        """
        if project.status == ProjectStatus.SUBMITTED:
            return True, "Project is in SUBMITTED status"
        
        if project.status != ProjectStatus.SANCTIONED:
            return False, f"Cannot update project in {project.status} status"
        
        if not project.allow_updates_after_approval:
            return False, "Project has been approved. Updates not allowed (BR-011)"
        
        return True, "Project allows post-approval updates"
    
    @staticmethod
    @transaction.atomic
    def update_project(
        project: Project,
        user: User,
        updates: Dict,
        change_reason: str,
        change_type: str
    ) -> Tuple[bool, str, Optional[ProjectVersion]]:
        """
        Update project and record version
        
        Args:
            project: Project to update
            user: User making the change
            updates: Dict of field updates {field: new_value}
            change_reason: Why the change was made
            change_type: Type of change (TITLE, BUDGET, etc.)
        
        Returns:
            (success, message, version_record)
        """
        # Validate can update
        can_update, reason = ProjectVersionService.can_update_project(project, user)
        if not can_update:
            return False, reason, None
        
        try:
            # Get current version count
            current_version = ProjectVersion.objects.filter(project=project).count()
            next_version = current_version + 1
            
            # Capture current state before update
            old_title = project.name
            old_description = project.description
            old_budget = project.total_budget
            
            # Apply updates
            allowed_fields = ['name', 'description', 'total_budget', 'allow_updates_after_approval']
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(project, field, value)
            
            # Record who and when updated
            project.last_updated_by = user
            project.last_updated_date = timezone.now()
            project.save()
            
            # Create version record
            version = ProjectVersion.objects.create(
                project=project,
                version_number=next_version,
                title=project.name,
                description=project.description,
                budget=project.total_budget,
                changed_by=user,
                change_reason=change_reason,
                change_type=change_type
            )
            
            # Trigger notification
            ProjectVersionService._notify_approvers(project, 'project_updated')
            
            return True, f"Project updated to version {next_version}", version
        
        except Exception as e:
            return False, f"Error updating project: {str(e)}", None
    
    @staticmethod
    def get_project_versions(project: Project, limit: int = 20) -> List[Dict]:
        """
        Get project version history (newest first)
        """
        versions = ProjectVersion.objects.filter(project=project).order_by('-version_number')[:limit]
        return [
            {
                'version_number': v.version_number,
                'title': v.title,
                'description': v.description,
                'budget': str(v.budget),
                'changed_by': v.changed_by.get_full_name() if v.changed_by else 'Unknown',
                'changed_date': v.changed_date.isoformat(),
                'change_reason': v.change_reason,
                'change_type': v.change_type
            }
            for v in versions
        ]
    
    @staticmethod
    def get_version_details(project: Project, version_number: int) -> Optional[Dict]:
        """
        Get specific version details
        """
        try:
            version = ProjectVersion.objects.get(project=project, version_number=version_number)
            return {
                'version_number': version.version_number,
                'project_id': project.pid,
                'project_name': project.name,
                'title': version.title,
                'description': version.description,
                'budget': str(version.budget),
                'changed_by': version.changed_by.get_full_name() if version.changed_by else 'Unknown',
                'changed_date': version.changed_date.isoformat(),
                'change_reason': version.change_reason,
                'change_type': version.change_type
            }
        except ProjectVersion.DoesNotExist:
            return None
    
    @staticmethod
    def _notify_approvers(project: Project, event_type: str):
        """Create notification for approvers about project update"""
        # Implementation would trigger notifications (UC-015 integration)
        pass


# ============================================================================
# UC-005: PROJECT CANCELLATION SERVICES
# ============================================================================

class ProjectCancellationService:
    """
    Handles project cancellation workflow (UC-005)
    BR-RSPC-07: Cancellation only before/during execution
    """
    
    @staticmethod
    def can_cancel_project(project: Project, user: User) -> Tuple[bool, str]:
        """
        Check if project can be cancelled
        BR-RSPC-07: Only if not already cancelled, before/during execution
        """
        if project.status == ProjectStatus.CANCELLED:
            return False, "Project is already cancelled"
        
        # Allowed statuses for cancellation
        allowed_statuses = [
            ProjectStatus.SUBMITTED,
            ProjectStatus.UNDER_REVIEW,
            ProjectStatus.SANCTIONED,
            ProjectStatus.ONGOING
        ]
        
        if project.status not in allowed_statuses:
            return False, f"Cannot cancel project in {project.status} status (BR-RSPC-07)"
        
        # Check user is PI or RSPC Admin or Dean
        try:
            extra_info = ExtraInfo.objects.get(user=user)
            is_pi = extra_info.user_type == 'faculty' and project.pi_id == user.username
            is_admin = extra_info.user_type == 'admin'
            
            if not (is_pi or is_admin):
                return False, "Only PI, RSPC Admin, or Dean can cancel project"
        except ExtraInfo.DoesNotExist:
            return False, "User profile not found"
        
        return True, "Project can be cancelled"
    
    @staticmethod
    @transaction.atomic
    def cancel_project(
        project: Project,
        user: User,
        cancellation_reason: str,
        mark_for_review: bool = False
    ) -> Tuple[bool, str]:
        """
        Cancel a project
        
        Actions:
        - Set status to CANCELLED
        - Record cancellation metadata
        - End active staff assignments
        - Cancel pending approvals
        - Notify all stakeholders
        """
        can_cancel, reason = ProjectCancellationService.can_cancel_project(project, user)
        if not can_cancel:
            return False, reason
        
        try:
            # Mark project as cancelled
            project.status = ProjectStatus.CANCELLED
            project.cancellation_reason = cancellation_reason
            project.cancelled_by = user
            project.cancelled_date = timezone.now()
            project.save()
            
            # End active staff assignments
            active_staff = Staff.objects.filter(
                pid=project,
                approval_status__in=['APPOINTED', 'HOD_APPROVED', 'RSPC_APPROVED']
            )
            for staff in active_staff:
                staff.approval_status = 'REJECTED'
                staff.save()
            
            # Notify all stakeholders
            ProjectCancellationService._notify_cancellation(project, user)
            
            return True, f"Project {project.pid} cancelled successfully"
        
        except Exception as e:
            return False, f"Error cancelling project: {str(e)}"
    
    @staticmethod
    def get_cancellation_details(project: Project) -> Optional[Dict]:
        """Get cancellation details of a project"""
        if project.status != ProjectStatus.CANCELLED or not project.cancelled_date:
            return None
        
        return {
            'project_id': project.pid,
            'project_name': project.name,
            'status': project.status,
            'cancellation_reason': project.cancellation_reason,
            'cancelled_by': project.cancelled_by.get_full_name() if project.cancelled_by else 'Unknown',
            'cancelled_date': project.cancelled_date.isoformat()
        }
    
    @staticmethod
    @transaction.atomic
    def create_cancellation_request(
        project: Project,
        user: User,
        reason: str
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Create formal cancellation request (workflow)
        PI requests, RSPC Admin approves
        """
        try:
            request = CancellationRequest.objects.create(
                project=project,
                requested_by=user,
                reason=reason,
                approval_status='PENDING'
            )
            
            # Notify RSPC Admin
            ProjectCancellationService._notify_cancellation_request(project, request)
            
            return True, f"Cancellation request {request.crid} created", request.crid
        except Exception as e:
            return False, f"Error creating cancellation request: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def approve_cancellation_request(
        request_id: int,
        user: User,
        approval_comments: str = ""
    ) -> Tuple[bool, str]:
        """
        RSPC Admin approves cancellation request and executes cancellation
        """
        try:
            cancellation_req = CancellationRequest.objects.get(crid=request_id)
            project = cancellation_req.project
            
            # Approve request
            cancellation_req.approval_status = 'APPROVED'
            cancellation_req.approved_by = user
            cancellation_req.approval_date = timezone.now()
            cancellation_req.save()
            
            # Cancel the project
            return ProjectCancellationService.cancel_project(
                project,
                user,
                cancellation_req.reason
            )
        except CancellationRequest.DoesNotExist:
            return False, "Cancellation request not found"
        except Exception as e:
            return False, f"Error approving cancellation: {str(e)}"
    
    @staticmethod
    def _notify_cancellation(project: Project, user: User):
        """Notify approvers and staff about cancellation"""
        pass
    
    @staticmethod
    def _notify_cancellation_request(project: Project, request: CancellationRequest):
        """Notify RSPC Admin about cancellation request"""
        pass


# ============================================================================
# UC-012: PROPOSAL VETTING SERVICES
# ============================================================================

class ProposalVettingService:
    """
    Handles HOD proposal vetting (UC-012)
    BR-RSPC-10: HOD vetting required before Director review
    """
    
    @staticmethod
    def can_vet_proposal(project: Project, user: User) -> Tuple[bool, str]:
        """
        Check if user (HOD) can vet this proposal
        
        Conditions:
        - Project must be in SUBMITTED status
        - User must be HOD of project's department
        """
        if project.status != ProjectStatus.SUBMITTED:
            return False, f"Project must be SUBMITTED, current status: {project.status}"
        
        if project.hod_vetting_status != 'PENDING':
            return False, f"Vetting already {project.hod_vetting_status}"
        
        # Check if user is HOD of the project's department
        try:
            extra_info = ExtraInfo.objects.get(user=user)
            
            # Check if user holds HOD designation
            hod_designation = HoldsDesignation.objects.filter(
                faculty__extra_info=extra_info,
                designation__name='Head of Department',
                is_current=True
            ).first()
            
            if not hod_designation:
                return False, "User is not a current HOD"
            
            # Check department alignment
            if hod_designation.designation.department.name != project.dept:
                return False, f"User is HOD of {hod_designation.designation.department.name}, not {project.dept}"
            
            return True, "User can vet this proposal"
        
        except ExtraInfo.DoesNotExist:
            return False, "User profile not found"
    
    @staticmethod
    @transaction.atomic
    def vet_proposal(
        project: Project,
        user: User,
        technical_feasibility: str,
        academic_relevance: str,
        resource_adequacy: str,
        department_alignment: str,
        comments: str = ""
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Record HOD vetting for proposal
        
        Each criterion: PASS, FAIL, FLAG
        Decision:
        - If all PASS: APPROVED → send to Director
        - If any FAIL: REJECTED → send back to PI
        - If FLAG: APPROVED (with flag noted) → send to Director with warning
        """
        can_vet, reason = ProposalVettingService.can_vet_proposal(project, user)
        if not can_vet:
            return False, reason, None
        
        try:
            # Create vetting record
            vetting = ProposalVetting.objects.create(
                project=project,
                vetted_by=user,
                technical_feasibility=technical_feasibility,
                academic_relevance=academic_relevance,
                resource_adequacy=resource_adequacy,
                department_alignment=department_alignment,
                comments=comments,
                vetting_completed_date=timezone.now()
            )
            
            # Determine outcome
            criteria = [
                technical_feasibility,
                academic_relevance,
                resource_adequacy,
                department_alignment
            ]
            
            has_fail = 'FAIL' in criteria
            
            if has_fail:
                vetting.status = 'REJECTED'
                project.hod_vetting_status = 'REJECTED'
                event_type = 'proposal_vetting_failed'
            else:
                vetting.status = 'APPROVED'
                project.hod_vetting_status = 'APPROVED'
                event_type = 'proposal_vetted'
            
            vetting.save()
            project.hod_vetting_date = timezone.now()
            project.save()
            
            # Trigger notifications
            ProposalVettingService._notify_vetting(project, event_type, vetting.status)
            
            return True, f"Vetting {event_type}", {
                'vetting_id': vetting.vetting_id,
                'status': vetting.status,
                'next_step': 'Director review' if vetting.status == 'APPROVED' else 'Return to PI'
            }
        
        except Exception as e:
            return False, f"Error vetting proposal: {str(e)}", None
    
    @staticmethod
    def get_vetting_details(project: Project) -> Optional[Dict]:
        """Get vetting details for a project"""
        try:
            vetting = ProposalVetting.objects.get(project=project)
            return {
                'vetting_id': vetting.vetting_id,
                'project_id': project.pid,
                'project_name': project.name,
                'vetted_by': vetting.vetted_by.get_full_name() if vetting.vetted_by else 'Unknown',
                'vetting_date': vetting.vetting_date.isoformat(),
                'technical_feasibility': vetting.technical_feasibility,
                'academic_relevance': vetting.academic_relevance,
                'resource_adequacy': vetting.resource_adequacy,
                'department_alignment': vetting.department_alignment,
                'comments': vetting.comments,
                'status': vetting.status,
                'vetting_completed_date': vetting.vetting_completed_date.isoformat() if vetting.vetting_completed_date else None
            }
        except ProposalVetting.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def revert_vetting(
        project: Project,
        user: User,
        reason: str
    ) -> Tuple[bool, str]:
        """
        HOD reverts vetting to change decision
        Only if not yet moved to Director
        """
        try:
            vetting = ProposalVetting.objects.get(project=project)
            
            # Only allow revert if project hasn't moved forward
            if project.status not in [ProjectStatus.SUBMITTED, ProjectStatus.UNDER_REVIEW]:
                return False, "Cannot revert vetting after project moved forward"
            
            # Reset to pending
            vetting.status = 'PENDING'
            vetting.vetting_completed_date = None
            vetting.comments = f"{vetting.comments}\n\n[Reverted by {user.get_full_name()} - Reason: {reason}]"
            vetting.save()
            
            project.hod_vetting_status = 'PENDING'
            project.hod_vetting_date = None
            project.save()
            
            # Notify approvers
            ProposalVettingService._notify_vetting(project, 'vetting_reverted', 'PENDING')
            
            return True, "Vetting reverted"
        
        except ProposalVetting.DoesNotExist:
            return False, "No vetting found for this project"
        except Exception as e:
            return False, f"Error reverting vetting: {str(e)}"
    
    @staticmethod
    def _notify_vetting(project: Project, event_type: str, status: str):
        """Send vetting notifications"""
        pass


# ============================================================================
# UC-013: DEPARTMENT PROJECT MANAGEMENT SERVICES
# ============================================================================

class DepartmentProjectsService:
    """
    HOD views of department projects (UC-013)
    BR-RSPC-11: HOD oversight of department projects
    """
    
    @staticmethod
    def get_hod_department(user: User) -> Optional[str]:
        """Get department of HOD user"""
        try:
            extra_info = ExtraInfo.objects.get(user=user)
            hod_designation = HoldsDesignation.objects.filter(
                faculty__extra_info=extra_info,
                designation__name='Head of Department',
                is_current=True
            ).first()
            
            if hod_designation:
                return hod_designation.designation.department.name
            return None
        except:
            return None
    
    @staticmethod
    def get_hod_projects(
        user: User,
        status_filter: Optional[str] = None,
        vetting_status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """
        Get all projects in HOD's department
        
        Returns: (project_list, total_count)
        """
        department = DepartmentProjectsService.get_hod_department(user)
        if not department:
            return [], 0
        
        # Base query
        projects = Project.objects.filter(dept=department)
        
        # Apply filters
        if status_filter:
            projects = projects.filter(status=status_filter)
        
        if vetting_status_filter:
            projects = projects.filter(hod_vetting_status=vetting_status_filter)
        
        total_count = projects.count()
        projects = projects.order_by('-submission_date')[offset:offset+limit]
        
        # Serialize
        result = [
            {
                'project_id': p.pid,
                'title': p.name,
                'pi_name': p.pi_name,
                'start_date': p.start_date.isoformat() if p.start_date else None,
                'end_date': p.end_date.isoformat() if p.end_date else None,
                'status': p.status,
                'hod_vetting_status': p.hod_vetting_status,
                'total_budget': str(p.total_budget),
                'department': p.dept
            }
            for p in projects
        ]
        
        return result, total_count
    
    @staticmethod
    def get_pending_vetting(user: User) -> Tuple[List[Dict], int]:
        """Get projects pending HOD vetting"""
        department = DepartmentProjectsService.get_hod_department(user)
        if not department:
            return [], 0
        
        projects = Project.objects.filter(
            dept=department,
            status=ProjectStatus.SUBMITTED,
            hod_vetting_status='PENDING'
        ).order_by('-submission_date')
        
        total_count = projects.count()
        
        result = [
            {
                'project_id': p.pid,
                'title': p.name,
                'pi_name': p.pi_name,
                'submitted_date': p.submission_date.isoformat(),
                'status': p.status,
                'total_budget': str(p.total_budget),
                'description': p.description[:200] + '...' if len(p.description) > 200 else p.description
            }
            for p in projects
        ]
        
        return result, total_count
    
    @staticmethod
    def get_hod_summary(user: User) -> Dict:
        """
        Get HOD dashboard summary
        BR-RSPC-11: HOD oversight summary
        """
        department = DepartmentProjectsService.get_hod_department(user)
        if not department:
            return {
                'error': 'User is not a HOD',
                'submitted': 0,
                'vetted': 0,
                'approved': 0,
                'rejected': 0
            }
        
        projects = Project.objects.filter(dept=department)
        
        summary = {
            'submitted': projects.filter(status=ProjectStatus.SUBMITTED).count(),
            'vetted': projects.filter(hod_vetting_status='APPROVED').count(),
            'approved': projects.filter(status=ProjectStatus.SANCTIONED).count(),
            'rejected': projects.filter(hod_vetting_status='REJECTED').count(),
            'ongoing': projects.filter(status=ProjectStatus.ONGOING).count(),
            'vetting_pending': projects.filter(
                status=ProjectStatus.SUBMITTED,
                hod_vetting_status='PENDING'
            ).count(),
            'total_projects': projects.count(),
            'department': department
        }
        
        # Calculate budget totals
        from django.db import models as django_models
        all_projects = projects.aggregate(
            total=django_models.Sum('total_budget'),
            sanctioned=django_models.Sum(
                django_models.Case(
                    django_models.When(status=ProjectStatus.SANCTIONED, then='total_budget'),
                    default=0,
                    output_field=django_models.DecimalField()
                )
            )
        )
        
        summary['total_budget'] = str(all_projects.get('total', 0) or 0)
        summary['sanctioned_budget'] = str(all_projects.get('sanctioned', 0) or 0)
        
        return summary

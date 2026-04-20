"""
RSPC Expenditure Approval System Services
UC-012, UC-013, BR-RSPC-13 Implementation

Critical: 3-tier approval based on amount
- Level 1 (≤₹50K): PI approves only
- Level 2 (₹50K-₹200K): PI approves → HOD approves
- Level 3 (>₹200K): PI approves → HOD approves → RSPC Admin approves
"""

from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation
from .models import (
    Expenditure, ExpenditureApprovalHistory, ExpenditureStatus, 
    ApprovalStage, CurrentApprover, Budget, Project
)
from .notification_service import NotificationService
from applications.notification.models import NotificationBase


class ExpenditureValidationService:
    """Validates expenditure requests before creation and approval"""
    
    MIN_PURPOSE_LENGTH = 20
    LEVEL1_MAX = Decimal('50000')
    LEVEL2_MAX = Decimal('200000')
    
    @classmethod
    def validate_expenditure_creation(cls, project, amount, category, purpose, supporting_docs):
        """
        Validate expenditure request (BR-RSPC-13)
        
        Rules:
        - Amount must be positive
        - Category must be valid
        - Purpose must be at least 20 chars
        - Cannot exceed budget for category
        - Supporting documents required if > 50K
        
        Returns: (is_valid, error_message)
        """
        errors = []
        
        # Amount validation
        if amount <= 0:
            errors.append("Amount must be positive")
        
        # Purpose validation
        if not purpose or len(purpose.strip()) < cls.MIN_PURPOSE_LENGTH:
            errors.append(f"Purpose must be at least {cls.MIN_PURPOSE_LENGTH} characters")
        
        # Budget validation
        if hasattr(project, 'budget') and project.budget:
            budget = project.budget
            category_budget = budget.get_category_budget(category)
            category_util = budget.get_category_utilization(category)
            available = category_budget - category_util
            
            if amount > available:
                errors.append(f"Insufficient budget. Available: ₹{available}")
        
        # Supporting documents validation
        if amount > cls.LEVEL1_MAX and not supporting_docs:
            errors.append("Supporting documents required for amounts > ₹50,000")
        
        return (len(errors) == 0, "; ".join(errors) if errors else "")
    
    @classmethod
    def can_user_approve(cls, user, expenditure, role):
        """
        Check if user can approve expenditure at this stage
        
        Rules:
        - Cannot approve own request (conflict of interest)
        - Must be current approver role
        - PI can only approve ≤ ₹50K
        - HOD can only approve ₹50K-₹200K
        - RSPC can approve > ₹200K
        """
        errors = []
        
        # Cannot approve own request
        if expenditure.requested_by == user:
            errors.append("Cannot approve own expenditure request (conflict of interest)")
        
        # Check if user is current approver
        if expenditure.current_approver != role:
            errors.append(f"Only {expenditure.current_approver} can approve at this stage")
        
        # Role-based amount validation
        if role == CurrentApprover.PI and expenditure.amount > cls.LEVEL1_MAX:
            errors.append(f"PI can only approve amounts ≤ ₹{cls.LEVEL1_MAX}")
        
        if role == CurrentApprover.HOD:
            if expenditure.amount <= cls.LEVEL1_MAX or expenditure.amount > cls.LEVEL2_MAX:
                errors.append(f"HOD can only approve amounts ₹{cls.LEVEL1_MAX}-₹{cls.LEVEL2_MAX}")
        
        if role == CurrentApprover.RSPC and expenditure.amount <= cls.LEVEL2_MAX:
            errors.append(f"RSPC can only approve amounts > ₹{cls.LEVEL2_MAX}")
        
        return (len(errors) == 0, "; ".join(errors) if errors else "")


class ExpenditureRoutingService:
    """Routes expenditures through approval chain based on amount (BR-RSPC-13)"""
    
    LEVEL1_MAX = Decimal('50000')
    LEVEL2_MAX = Decimal('200000')
    
    @classmethod
    def get_approval_tier(cls, amount):
        """Get approval tier based on amount"""
        if amount <= cls.LEVEL1_MAX:
            return 1  # PI only
        elif amount <= cls.LEVEL2_MAX:
            return 2  # PI + HOD
        else:
            return 3  # PI + HOD + RSPC
    
    @classmethod
    def get_initial_approver_role(cls, amount):
        """Get initial approver (always PI at start)"""
        return CurrentApprover.PI
    
    @classmethod
    def get_next_approver_role(cls, expenditure):
        """
        Get next approver in chain (BR-RSPC-13)
        
        Returns: (next_role, next_stage) or (None, None) if approval complete
        """
        tier = cls.get_approval_tier(expenditure.amount)
        
        if tier == 1:
            # Level 1: PI only - no more stages
            return (None, None)
        elif tier == 2:
            # Level 2: PI → HOD
            if expenditure.current_stage == ApprovalStage.PI:
                return (CurrentApprover.HOD, ApprovalStage.HOD)
            return (None, None)
        else:  # tier == 3
            # Level 3: PI → HOD → RSPC
            if expenditure.current_stage == ApprovalStage.PI:
                return (CurrentApprover.HOD, ApprovalStage.HOD)
            elif expenditure.current_stage == ApprovalStage.HOD:
                return (CurrentApprover.RSPC, ApprovalStage.RSPC)
            return (None, None)
    
    @classmethod
    def route_to_next_approver(cls, expenditure):
        """Route expenditure to next approver or mark as APPROVED"""
        next_role, next_stage = cls.get_next_approver_role(expenditure)
        
        if next_role is None:
            # Approval complete
            expenditure.status = ExpenditureStatus.APPROVED
            expenditure.current_approver = None
            expenditure.current_stage = ApprovalStage.PI
        else:
            # Route to next approver
            expenditure.current_approver = next_role
            expenditure.current_stage = next_stage
            
            # Update status based on stage
            if next_role == CurrentApprover.HOD:
                expenditure.status = ExpenditureStatus.PI_APPROVED
            elif next_role == CurrentApprover.RSPC:
                expenditure.status = ExpenditureStatus.HOD_APPROVED
        
        expenditure.save()
        return expenditure


class ExpenditureApprovalService:
    """Handles approval and rejection workflow"""
    
    @staticmethod
    @transaction.atomic
    def create_expenditure(project, amount, category, purpose, requested_by, supporting_docs=None):
        """
        UC-012: Create expenditure request with automatic routing
        
        Business Rules (BR-RSPC-13):
        - Amount determines approval tier
        - Automatically route to correct approver
        - Reject if budget insufficient
        - Require supporting docs if > ₹50K
        
        Returns: (success, expenditure_or_error)
        """
        try:
            # Validate
            is_valid, error_msg = ExpenditureValidationService.validate_expenditure_creation(
                project, amount, category, purpose, supporting_docs
            )
            
            if not is_valid:
                return (False, error_msg)
            
            # Create expenditure
            expenditure = Expenditure.objects.create(
                project=project,
                amount=amount,
                category=category,
                purpose=purpose,
                requested_by=requested_by,
                status=ExpenditureStatus.PENDING,
                current_approver=CurrentApprover.PI,
                current_stage=ApprovalStage.PI,
                supporting_documents=supporting_docs or [],
                approval_chain={}
            )
            
            # Send notification to PI
            ExpenditureNotificationService.notify_pending_approval(expenditure)
            
            return (True, expenditure)
        
        except Exception as e:
            return (False, str(e))
    
    @staticmethod
    @transaction.atomic
    def approve_expenditure(expenditure, approver, approver_role, comments=""):
        """
        Approve expenditure at current stage
        
        Business Rules:
        - Cannot approve own request
        - Must be current approver
        - Role-based amount validation
        - Auto-route to next approver or mark APPROVED
        
        Returns: (success, message)
        """
        try:
            # Validate
            can_approve, error_msg = ExpenditureValidationService.can_user_approve(
                approver, expenditure, approver_role
            )
            
            if not can_approve:
                return (False, error_msg)
            
            # Record approval in history
            history = ExpenditureApprovalHistory.objects.create(
                expenditure=expenditure,
                approver=approver,
                approver_role=approver_role,
                action='APPROVED',
                comments=comments
            )
            
            # Update approval chain
            stage_key = approver_role.lower()
            expenditure.approval_chain[stage_key] = {
                'approver': approver.user.username if hasattr(approver, 'user') else str(approver),
                'approved_at': datetime.now().isoformat(),
                'comments': comments
            }
            
            # Route to next approver
            ExpenditureRoutingService.route_to_next_approver(expenditure)
            expenditure.save()
            
            # Send notifications
            if expenditure.status == ExpenditureStatus.APPROVED:
                ExpenditureNotificationService.notify_approval_complete(expenditure)
            else:
                ExpenditureNotificationService.notify_pending_approval(expenditure)
            
            return (True, f"Expenditure approved and routed to {expenditure.current_approver or 'completed'}")
        
        except Exception as e:
            return (False, str(e))
    
    @staticmethod
    @transaction.atomic
    def reject_expenditure(expenditure, rejecter, rejecter_role, reason=""):
        """
        Reject expenditure (can reject at any level)
        
        Business Rules:
        - Rejection sends back to PI
        - Store rejection reason
        - Update status
        
        Returns: (success, message)
        """
        try:
            # Record rejection
            history = ExpenditureApprovalHistory.objects.create(
                expenditure=expenditure,
                approver=rejecter,
                approver_role=rejecter_role,
                action='REJECTED',
                comments=reason
            )
            
            # Update approval chain
            stage_key = rejecter_role.lower()
            expenditure.approval_chain[stage_key] = {
                'approver': rejecter.user.username if hasattr(rejecter, 'user') else str(rejecter),
                'approved_at': datetime.now().isoformat(),
                'action': 'REJECTED',
                'comments': reason
            }
            
            # Reset to PI for resubmission
            expenditure.status = ExpenditureStatus.REJECTED
            expenditure.current_approver = CurrentApprover.PI
            expenditure.current_stage = ApprovalStage.PI
            expenditure.save()
            
            # Notify PI of rejection
            ExpenditureNotificationService.notify_rejection(expenditure, reason)
            
            return (True, "Expenditure rejected. Sent back to PI for revision.")
        
        except Exception as e:
            return (False, str(e))


class ExpenditureNotificationService:
    """
    Handles all expenditure notifications with integration to NotificationService
    Sends notifications for all 3 expenditure event types
    """
    
    @staticmethod
    def _get_approver_user(project, approver_role):
        """Get Django User object for the approver role"""
        try:
            if approver_role == CurrentApprover.PI:
                # Get PI user
                return User.objects.get(username=project.pi_id)
            elif approver_role == CurrentApprover.HOD:
                # Get HOD of project's department
                # This is simplified - in real system get from designation
                extra_info = ExtraInfo.objects.filter(
                    user__groups__name='HOD',
                    department__name=project.dept
                ).first()
                return extra_info.user if extra_info else None
            elif approver_role == CurrentApprover.RSPC:
                # Get any RSPC Admin
                extra_info = ExtraInfo.objects.filter(
                    user__groups__name='RSPC_Admin'
                ).first()
                return extra_info.user if extra_info else None
        except Exception as e:
            print(f"Error getting approver user: {e}")
            return None
    
    @staticmethod
    def notify_pending_approval(expenditure):
        """
        UC-015: Send notification when expenditure is pending approval
        Event: expenditure_pending_approval
        """
        try:
            approver_user = ExpenditureNotificationService._get_approver_user(
                expenditure.project, expenditure.current_approver
            )
            
            if not approver_user:
                return False
            
            # Use new NotificationService
            NotificationService.notify_expenditure_pending_approval(
                expenditure=expenditure,
                approver_user=approver_user,
                approver_role=expenditure.current_approver
            )
            return True
        
        except Exception as e:
            print(f"Notification error: {e}")
            return False
    
    @staticmethod
    def notify_approval_complete(expenditure):
        """
        UC-015: Send notification to PI when expenditure is fully approved
        Event: expenditure_approved
        """
        try:
            # Get PI user
            pi_user = User.objects.get(username=expenditure.project.pi_id)
            
            # Get the approver who made final approval (from history)
            final_approval = ExpenditureApprovalHistory.objects.filter(
                expenditure=expenditure,
                action='APPROVED'
            ).order_by('-approved_at').first()
            
            approver_role = final_approval.approver_role if final_approval else 'RSPC'
            
            # Use new NotificationService
            NotificationService.notify_expenditure_approved(
                expenditure=expenditure,
                pi_user=pi_user,
                approver_role=approver_role
            )
            return True
        except Exception as e:
            print(f"Notification error: {e}")
            return False
    
    @staticmethod
    def notify_rejection(expenditure, reason):
        """
        UC-015: Send notification to PI when expenditure is rejected
        Event: expenditure_rejected
        """
        try:
            # Get PI user
            pi_user = User.objects.get(username=expenditure.project.pi_id)
            
            # Use new NotificationService
            NotificationService.notify_expenditure_rejected(
                expenditure=expenditure,
                pi_user=pi_user,
                rejection_reason=reason
            )
            return True
        except Exception as e:
            print(f"Notification error: {e}")
            return False


class ExpenditureQueryService:
    """Query and filtering for expenditure lists"""
    
    @staticmethod
    def get_user_role(user):
        """Determine user's role in RSPC context"""
        try:
            extra_info = ExtraInfo.objects.get(user=user)
            
            # Check if RSPC Admin
            if extra_info.user.groups.filter(name='RSPC_Admin').exists():
                return 'RSPC'
            
            # Check if HOD
            if HoldsDesignation.objects.filter(
                extra_info=extra_info,
                designation__title__contains='HOD'
            ).exists():
                return 'HOD'
            
            # Otherwise, assume PI
            return 'PI'
        except:
            return 'PI'
    
    @staticmethod
    def get_filtered_expenditures(user, role=None):
        """
        UC-013: Get expenditures visible to user
        
        Role-based filtering:
        - PI: Own expenditures
        - HOD: Expenditures needing HOD approval
        - RSPC Admin: All expenditures for review
        """
        if not role:
            role = ExpenditureQueryService.get_user_role(user)
        
        try:
            extra_info = ExtraInfo.objects.get(user=user)
        except:
            return Expenditure.objects.none()
        
        if role == 'RSPC':
            # RSPC Admin sees all
            return Expenditure.objects.all()
        
        elif role == 'HOD':
            # HOD sees:
            # 1. Their pending approvals (HOD stage)
            # 2. Their department's expenditures
            from .models import Project
            hod_projects = Project.objects.filter(dept=extra_info.department)
            
            return Expenditure.objects.filter(
                project__in=hod_projects
            )
        
        else:  # PI
            # PI sees own and their projects' expenditures
            pi_projects = Project.objects.filter(pi_id=extra_info.user.username)
            return Expenditure.objects.filter(
                project__in=pi_projects
            )
    
    @staticmethod
    def get_approval_pending_for_user(user, role=None):
        """Get expenditures pending this user's approval"""
        if not role:
            role = ExpenditureQueryService.get_user_role(user)
        
        return ExpenditureQueryService.get_filtered_expenditures(user, role).filter(
            current_approver=role,
            status__in=[ExpenditureStatus.PENDING, ExpenditureStatus.PI_APPROVED, ExpenditureStatus.HOD_APPROVED]
        )


class ExpenditureApprovalService:
    """Extended service with utility methods"""
    
    @staticmethod
    def _get_approver_user(project, approver_role):
        """Get User object for approver role"""
        try:
            if approver_role == CurrentApprover.PI:
                return User.objects.get(username=project.pi_id)
            
            elif approver_role == CurrentApprover.HOD:
                # Get HOD for project's department
                extra_info = ExtraInfo.objects.get(department=project.dept)
                return extra_info.user
            
            elif approver_role == CurrentApprover.RSPC:
                # Get RSPC admin group user
                from django.contrib.auth.models import Group, User
                rspc_group = Group.objects.get(name='RSPC_Admin')
                return rspc_group.user_set.first()
        
        except:
            return None

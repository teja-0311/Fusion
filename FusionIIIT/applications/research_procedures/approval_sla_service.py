"""
BR-018: Approval Timeframe & SLA Services
Handles automatic approval deadline calculation and escalation
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal

from .models import (
    ApprovalSLA, Expenditure, Project, Staff, ProgressReport, ProjectClosure,
    ApprovalSLAStatus, ApprovalSLAEntityType, CurrentApprover
)
from .notification_service import NotificationService
from applications.globals.models import ExtraInfo


class ApprovalSLAService:
    """Service for managing approval SLAs (BR-018)"""
    
    # Approval timeframes based on BR-018
    TIMEFRAME_RULES = {
        'expenditure_tier_1': 3,      # ≤50K: 3 days
        'expenditure_tier_2': 5,      # 50K-200K: 5 days
        'expenditure_tier_3': 7,      # >200K: 7 days
        'project_proposal': 10,       # Project proposals: 10 days
        'staff': 7,                   # Staff: 7 days
        'progress_report': 5,         # Progress reports: 5 days
        'project_closure': 10,        # Project closure: 10 days
    }
    
    @staticmethod
    def calculate_approval_deadline(entity_type: str, entity_id: str, created_date: timezone.datetime = None) -> timezone.datetime:
        """
        Calculate approval deadline based on entity type and BR-018 rules
        
        Args:
            entity_type: Type of entity (expenditure, project, staff, etc.)
            entity_id: ID of the entity
            created_date: When entity was created (defaults to now)
        
        Returns:
            Deadline datetime
        """
        if created_date is None:
            created_date = timezone.now()
        
        days = 5  # Default
        
        if entity_type == ApprovalSLAEntityType.EXPENDITURE:
            # Get expenditure and calculate based on amount
            try:
                exp = Expenditure.objects.get(eid=entity_id)
                if exp.amount <= 50000:
                    days = ApprovalSLAService.TIMEFRAME_RULES['expenditure_tier_1']
                elif exp.amount <= 200000:
                    days = ApprovalSLAService.TIMEFRAME_RULES['expenditure_tier_2']
                else:
                    days = ApprovalSLAService.TIMEFRAME_RULES['expenditure_tier_3']
            except Expenditure.DoesNotExist:
                pass
        
        elif entity_type == ApprovalSLAEntityType.PROJECT:
            days = ApprovalSLAService.TIMEFRAME_RULES['project_proposal']
        
        elif entity_type == ApprovalSLAEntityType.STAFF:
            days = ApprovalSLAService.TIMEFRAME_RULES['staff']
        
        elif entity_type == ApprovalSLAEntityType.PROGRESS_REPORT:
            days = ApprovalSLAService.TIMEFRAME_RULES['progress_report']
        
        elif entity_type == ApprovalSLAEntityType.PROJECT_CLOSURE:
            days = ApprovalSLAService.TIMEFRAME_RULES['project_closure']
        
        return created_date + timedelta(days=days)
    
    @staticmethod
    def create_approval_sla(entity_type: str, entity_id: str, current_approver_user, created_date: timezone.datetime = None):
        """
        Create an approval SLA record for an entity
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            current_approver_user: User who is current approver
            created_date: When entity was created
        """
        if created_date is None:
            created_date = timezone.now()
        
        deadline = ApprovalSLAService.calculate_approval_deadline(entity_type, entity_id, created_date)
        
        # Create or update SLA
        sla, created = ApprovalSLA.objects.update_or_create(
            entity_type=entity_type,
            entity_id=str(entity_id),
            defaults={
                'created_date': created_date,
                'deadline': deadline,
                'current_approver': current_approver_user,
                'escalation_level': 1,
                'status': ApprovalSLAStatus.PENDING,
            }
        )
        
        return sla
    
    @staticmethod
    def check_and_escalate_approvals():
        """
        Scheduled task to check for overdue approvals and escalate
        Runs every hour
        
        1. Find all PENDING SLAs past their deadline
        2. Send timeout notifications (1 day before, at deadline, 1 day after)
        3. Auto-escalate to next level if past deadline
        4. Log escalations
        """
        now = timezone.now()
        one_day_ago = now - timedelta(days=1)
        one_day_from_now = now + timedelta(days=1)
        
        # Find SLAs that need attention
        pending_slas = ApprovalSLA.objects.filter(status=ApprovalSLAStatus.PENDING)
        
        for sla in pending_slas:
            # 1. Send reminder if 1 day before deadline
            if one_day_ago <= sla.deadline < now:
                if not sla.timeout_notified:
                    ApprovalSLAService._send_deadline_approaching_notification(sla)
                    sla.timeout_notified = True
                    sla.save()
            
            # 2. Check if past deadline - escalate
            if sla.deadline < now:
                # Auto-escalate to next level
                ApprovalSLAService._escalate_approval(sla)
        
        return pending_slas.count()
    
    @staticmethod
    def _send_deadline_approaching_notification(sla):
        """Send notification that deadline is approaching"""
        try:
            if sla.current_approver:
                entity_type = sla.entity_type
                entity_name = ApprovalSLAService._get_entity_name(sla)
                
                NotificationService.notify_approval_deadline_approaching(
                    sla.current_approver,
                    entity_type,
                    entity_name
                )
        except Exception as e:
            pass
    
    @staticmethod
    def _escalate_approval(sla):
        """Escalate approval to next level"""
        try:
            # Determine next escalation level
            next_level = sla.escalation_level + 1
            
            if next_level <= 3:
                # Get next approver based on entity type
                next_approver = ApprovalSLAService._get_next_approver(sla.entity_type, next_level)
                
                if next_approver:
                    # Update SLA
                    sla.escalation_level = next_level
                    sla.current_approver = next_approver
                    sla.status = ApprovalSLAStatus.ESCALATED
                    sla.escalation_date = timezone.now()
                    sla.timeout_notified = False
                    sla.save()
                    
                    # Send escalation notification
                    entity_name = ApprovalSLAService._get_entity_name(sla)
                    NotificationService.notify_approval_escalated(
                        next_approver,
                        sla.entity_type,
                        entity_name
                    )
                    
                    # Mark entity as escalated
                    ApprovalSLAService._mark_entity_escalated(sla)
                else:
                    # Max escalation reached - mark as timeout
                    sla.status = ApprovalSLAStatus.TIMEOUT
                    sla.save()
            else:
                # Max escalation reached
                sla.status = ApprovalSLAStatus.TIMEOUT
                sla.save()
        
        except Exception as e:
            pass
    
    @staticmethod
    def _get_next_approver(entity_type: str, escalation_level: int):
        """Get next approver based on entity type and escalation level"""
        try:
            # Get RSPC Admin or Director
            if escalation_level == 2:
                # Second level - HOD or equivalent
                admin_extra = ExtraInfo.objects.filter(
                    designation__name__in=['HOD', 'Head of Department']
                ).first()
            elif escalation_level >= 3:
                # Third level - Director or RSPC Admin
                admin_extra = ExtraInfo.objects.filter(
                    designation__name__in=['Director', 'RSPC Admin', 'RSPC_ADMIN']
                ).first()
            else:
                return None
            
            if admin_extra and admin_extra.user:
                return admin_extra.user
        except Exception as e:
            pass
        
        return None
    
    @staticmethod
    def _mark_entity_escalated(sla):
        """Mark entity as escalated in its model"""
        try:
            if sla.entity_type == ApprovalSLAEntityType.EXPENDITURE:
                exp = Expenditure.objects.get(eid=sla.entity_id)
                exp.approval_status_escalated = True
                exp.escalation_date = sla.escalation_date
                exp.save()
            
            elif sla.entity_type == ApprovalSLAEntityType.PROJECT:
                proj = Project.objects.get(pid=sla.entity_id)
                proj.approval_status_escalated = True
                proj.escalation_date = sla.escalation_date
                proj.save()
            
            elif sla.entity_type == ApprovalSLAEntityType.STAFF:
                staff = Staff.objects.get(sid=sla.entity_id)
                staff.approval_status_escalated = True
                staff.escalation_date = sla.escalation_date
                staff.save()
        
        except Exception as e:
            pass
    
    @staticmethod
    def _get_entity_name(sla):
        """Get human-readable name for entity"""
        try:
            if sla.entity_type == ApprovalSLAEntityType.EXPENDITURE:
                exp = Expenditure.objects.get(eid=sla.entity_id)
                return f"Expenditure {exp.eid}: ₹{exp.amount}"
            elif sla.entity_type == ApprovalSLAEntityType.PROJECT:
                proj = Project.objects.get(pid=sla.entity_id)
                return f"Project {proj.pid}: {proj.name}"
            elif sla.entity_type == ApprovalSLAEntityType.STAFF:
                staff = Staff.objects.get(sid=sla.entity_id)
                return f"Staff {staff.sid}: {staff.person}"
            elif sla.entity_type == ApprovalSLAEntityType.PROGRESS_REPORT:
                report = ProgressReport.objects.get(prid=sla.entity_id)
                return f"Report {report.prid}: {report.project.name}"
            elif sla.entity_type == ApprovalSLAEntityType.PROJECT_CLOSURE:
                closure = ProjectClosure.objects.get(closure_id=sla.entity_id)
                return f"Closure {closure.closure_id}: {closure.project.name}"
        except Exception as e:
            pass
        
        return f"{sla.entity_type} {sla.entity_id}"

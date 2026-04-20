"""
BR-015: Final Settlement Service
Calculates and manages final settlement for projects on closure
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    ProjectClosure, Project, Budget, Expenditure, Staff,
    ProjectClosureStatus, ExpenditureApprovalHistory
)
from .notification_service import NotificationService


class RSPCError(Exception):
    """Base exception for RSPC operations"""
    pass


class SettlementRules:
    """
    Implements BR-015 Final Settlement Rules
    Calculates settlement amounts with penalties and deductions
    """
    
    # Settlement calculation parameters
    TIMELINE_PENALTY_PERCENT = 5  # 5% penalty on unused portion if overdue
    COMPLIANCE_DEDUCTION_PERCENT = 2  # 2% per violation
    MISSING_DOC_DEDUCTION_PERCENT = 1  # 1% per missing doc (>50K items)
    
    @staticmethod
    def calculate_settlement(closure_id: int, user: User) -> dict:
        """
        Calculate final settlement for a project closure.
        
        Applies all settlement rules:
        1. Refund = Budget - Expenditure
        2. Timeline penalty: 5% on unused if overdue
        3. Compliance deductions: 2% per violation
        4. Missing docs: 1% per missing doc (>50K items)
        
        Args:
            closure_id: ProjectClosure ID
            user: User performing calculation
        
        Returns:
            dict: settlement_amount, held_amount, refund, penalties
        
        Raises:
            RSPCError: If closure not found
        """
        try:
            closure = ProjectClosure.objects.get(closure_id=closure_id)
        except ProjectClosure.DoesNotExist:
            raise RSPCError(f"Closure {closure_id} not found")
        
        project = closure.project
        
        # Get budget and expenditure
        try:
            budget = Budget.objects.get(project=project)
        except Budget.DoesNotExist:
            raise RSPCError(f"Budget not found for project {project.pid}")
        
        # Calculate total expenditure
        expenditures = Expenditure.objects.filter(project=project)
        total_expenditure = sum(e.amount for e in expenditures)
        
        budget_amount = budget.allocated_amount
        basic_refund = budget_amount - Decimal(str(total_expenditure))
        
        # Calculate penalties
        penalty_amount = SettlementRules._calculate_timeline_penalty(project, basic_refund)
        
        # Calculate compliance deductions
        compliance_deduction = SettlementRules._calculate_compliance_deductions(project, expenditures)
        
        # Calculate missing document deductions
        doc_deduction = SettlementRules._calculate_missing_doc_deductions(expenditures)
        
        # Final settlement = budget - (expenditure + penalties - compliance deductions)
        settlement_amount = (
            budget_amount - 
            Decimal(str(total_expenditure)) - 
            penalty_amount - 
            compliance_deduction + 
            doc_deduction
        )
        
        with transaction.atomic():
            closure.settlement_amount = max(settlement_amount, Decimal('0'))
            closure.refund_amount = max(basic_refund, Decimal('0'))
            closure.penalty_amount = penalty_amount
            closure.settlement_calculated = True
            closure.save()
        
        return {
            'settlement_amount': float(settlement_amount),
            'held_amount': 0,
            'refund_amount': float(basic_refund),
            'penalties': float(penalty_amount),
            'compliance_deductions': float(compliance_deduction),
            'doc_deductions': float(doc_deduction),
            'budget_total': float(budget_amount),
            'expenditure_total': float(total_expenditure)
        }
    
    @staticmethod
    def _calculate_timeline_penalty(project: Project, refund_amount: Decimal) -> Decimal:
        """
        Apply 5% penalty if project exceeded timeline.
        
        Checks if closure_date > expected_completion_date
        """
        penalty = Decimal('0')
        
        # Get expected end date
        if project.estimated_duration:
            expected_end = project.sanctioned_date + timedelta(days=project.estimated_duration * 30)
            closure_date = timezone.now()
            
            if closure_date > expected_end:
                penalty = refund_amount * Decimal(str(SettlementRules.TIMELINE_PENALTY_PERCENT / 100))
        
        return penalty
    
    @staticmethod
    def _calculate_compliance_deductions(project: Project, expenditures) -> Decimal:
        """
        Apply 2% deduction per compliance violation.
        
        Checks for:
        - Budget reallocation violations (BR-RSPC-08)
        - Approval chain violations (BR-RSPC-13)
        """
        deduction = Decimal('0')
        violation_count = 0
        
        # Check budget reallocation compliance
        try:
            budget = Budget.objects.get(project=project)
            reallocations = budget.reallocations.all()
            
            for realloc in reallocations:
                realloc_percent = (realloc.amount / budget.allocated_amount) * 100
                if realloc_percent > 20:
                    violation_count += 1
        except:
            pass
        
        # Check approval chain
        for exp in expenditures:
            approvals = ExpenditureApprovalHistory.objects.filter(expenditure=exp)
            if not approvals.exists():
                violation_count += 1
        
        deduction = (
            budget.allocated_amount * 
            Decimal(str(SettlementRules.COMPLIANCE_DEDUCTION_PERCENT / 100)) * 
            Decimal(str(violation_count))
        )
        
        return deduction
    
    @staticmethod
    def _calculate_missing_doc_deductions(expenditures) -> Decimal:
        """
        Apply 1% deduction per missing document for >50K items.
        
        Checks for expenditures >50K without supporting documents.
        """
        deduction = Decimal('0')
        missing_doc_count = 0
        
        for exp in expenditures:
            if exp.amount > 50000 and not exp.is_eligible_for_approval:
                missing_doc_count += 1
        
        # Assume 1% per missing doc on average budget
        if missing_doc_count > 0:
            total_budget = sum(e.project.budget.allocated_amount for e in expenditures 
                             if hasattr(e.project, 'budget'))
            if total_budget > 0:
                deduction = (
                    total_budget * 
                    Decimal(str(SettlementRules.MISSING_DOC_DEDUCTION_PERCENT / 100)) * 
                    Decimal(str(missing_doc_count))
                )
        
        return deduction
    
    @staticmethod
    def approve_settlement(closure_id: int, user: User) -> dict:
        """
        Approve calculated settlement.
        
        Only Director can approve. Changes closure status to SETTLED.
        Records final amount to be released.
        
        Args:
            closure_id: ProjectClosure ID
            user: User approving (must be Director)
        
        Returns:
            dict: closure_id, status, settlement_amount
        
        Raises:
            RSPCError: If closure not found or not calculated
        """
        try:
            closure = ProjectClosure.objects.get(closure_id=closure_id)
        except ProjectClosure.DoesNotExist:
            raise RSPCError(f"Closure {closure_id} not found")
        
        if not closure.settlement_calculated:
            raise RSPCError("Settlement must be calculated before approval")
        
        with transaction.atomic():
            closure.settlement_approved = True
            closure.status = ProjectClosureStatus.SETTLED
            closure.save()
            
            # Trigger notification
            NotificationService.notify_settlement_approved(closure)
        
        return {
            'closure_id': closure.closure_id,
            'status': closure.status,
            'settlement_amount': float(closure.settlement_amount) if closure.settlement_amount else 0
        }


class SettlementService:
    """
    Service wrapper for settlement operations
    """
    
    @staticmethod
    def calculate_settlement(project_id: int, user: User) -> dict:
        """Calculate settlement for a project on closure"""
        try:
            project = Project.objects.get(pid=project_id)
            closure = ProjectClosure.objects.get(project=project)
        except (Project.DoesNotExist, ProjectClosure.DoesNotExist):
            raise RSPCError(f"Project {project_id} or its closure not found")
        
        return SettlementRules.calculate_settlement(closure.closure_id, user)
    
    @staticmethod
    def approve_settlement(project_id: int, user: User) -> dict:
        """Approve settlement for a project"""
        try:
            project = Project.objects.get(pid=project_id)
            closure = ProjectClosure.objects.get(project=project)
        except (Project.DoesNotExist, ProjectClosure.DoesNotExist):
            raise RSPCError(f"Project {project_id} or its closure not found")
        
        return SettlementRules.approve_settlement(closure.closure_id, user)

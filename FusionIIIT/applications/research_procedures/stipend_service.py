"""
UC-017: Stipend Disbursement Service
Handles stipend batch creation, approval, and disbursement workflows
"""

from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    StipendBatch, StipendDisbursement, Staff, Project,
    StipendBatchStatus, StipendDisbursementStatus, PaymentMethod
)
from .notification_service import NotificationService


class RSPCError(Exception):
    """Base exception for RSPC operations"""
    pass


class StipendService:
    """
    Service for managing stipend disbursement workflows
    Implements UC-017 requirements
    """
    
    @staticmethod
    def create_batch(project_id: int, month: str) -> dict:
        """
        Create a stipend batch for a project in a given month.
        
        Fetches all active staff for the project in that month and creates
        disbursement records. Prevents duplicate batches.
        
        Args:
            project_id: Project ID
            month: Month in 'YYYY-MM-01' format (start of month)
        
        Returns:
            dict: batch_id, staff_count, total_amount
        
        Raises:
            RSPCError: If batch already exists or no active staff
        """
        try:
            month_date = datetime.strptime(month, '%Y-%m-%d').date()
        except ValueError:
            raise RSPCError("Invalid month format. Use YYYY-MM-01")
        
        # Check if batch already exists (unique constraint)
        try:
            project = Project.objects.get(pid=project_id)
        except Project.DoesNotExist:
            raise RSPCError(f"Project {project_id} not found")
        
        existing_batch = StipendBatch.objects.filter(
            project=project,
            month=month_date
        ).first()
        
        if existing_batch:
            raise RSPCError(f"Batch already exists for {month} on project {project_id}")
        
        # Get all active staff for this project in this month
        active_staff = Staff.objects.filter(
            pid=project,
            start_date__lte=timezone.now(),
            approval_status='APPROVED'
        )
        
        if not active_staff.exists():
            raise RSPCError(f"No active staff found for project {project_id} in {month}")
        
        with transaction.atomic():
            # Create batch
            batch = StipendBatch.objects.create(
                project=project,
                month=month_date,
                disbursement_count=active_staff.count()
            )
            
            total_amount = Decimal('0.00')
            
            # Create disbursement records for each staff
            for staff in active_staff:
                # Calculate stipend amount (from staff.salary_per_month)
                stipend_amount = staff.salary_per_month or staff.salary
                
                StipendDisbursement.objects.create(
                    staff=staff,
                    project=project,
                    month=month_date,
                    stipend_amount=stipend_amount,
                    status=StipendDisbursementStatus.PENDING
                )
                
                total_amount += stipend_amount
            
            # Update batch total
            batch.total_amount = total_amount
            batch.save()
            
            return {
                'batch_id': batch.id,
                'staff_count': active_staff.count(),
                'total_amount': float(total_amount)
            }
    
    @staticmethod
    def approve_batch(batch_id: int, user: User) -> dict:
        """
        Approve a batch for disbursement.
        
        Changes batch status from PENDING to APPROVED.
        Updates all disbursements to ready status.
        
        Args:
            batch_id: Batch ID
            user: User performing approval
        
        Returns:
            dict: batch_id, status, approval_date
        
        Raises:
            RSPCError: If batch not found or not in PENDING status
        """
        try:
            batch = StipendBatch.objects.get(id=batch_id)
        except StipendBatch.DoesNotExist:
            raise RSPCError(f"Batch {batch_id} not found")
        
        if batch.status != StipendBatchStatus.PENDING:
            raise RSPCError(f"Batch must be in PENDING status to approve. Current: {batch.status}")
        
        with transaction.atomic():
            batch.status = StipendBatchStatus.APPROVED
            batch.approved_by = user
            batch.approval_date = timezone.now()
            batch.save()
            
            # Trigger notification
            NotificationService.notify_stipend_batch_approved(batch)
        
        return {
            'batch_id': batch.id,
            'status': batch.status,
            'approval_date': batch.approval_date.isoformat() if batch.approval_date else None
        }
    
    @staticmethod
    def disburse_batch(batch_id: int, payment_details: dict) -> dict:
        """
        Mark batch as DISBURSED (actual payment outside system).
        
        Updates all disbursements to DISBURSED status and records payment details.
        
        Args:
            batch_id: Batch ID
            payment_details: dict with payment_method, payment_reference
        
        Returns:
            dict: batch_id, status, disbursed_count
        
        Raises:
            RSPCError: If batch not found or not APPROVED
        """
        try:
            batch = StipendBatch.objects.get(id=batch_id)
        except StipendBatch.DoesNotExist:
            raise RSPCError(f"Batch {batch_id} not found")
        
        if batch.status != StipendBatchStatus.APPROVED:
            raise RSPCError(f"Batch must be APPROVED to disburse. Current: {batch.status}")
        
        with transaction.atomic():
            disbursements = StipendDisbursement.objects.filter(
                project=batch.project,
                month=batch.month,
                status=StipendDisbursementStatus.PENDING
            )
            
            payment_method = payment_details.get('payment_method', PaymentMethod.BANK)
            payment_reference = payment_details.get('payment_reference', '')
            
            disbursed_count = 0
            for disbursement in disbursements:
                disbursement.status = StipendDisbursementStatus.DISBURSED
                disbursement.disbursement_date = timezone.now()
                disbursement.payment_method = payment_method
                disbursement.payment_reference = payment_reference
                disbursement.save()
                
                # Trigger notification to staff
                NotificationService.notify_stipend_disbursed(disbursement)
                disbursed_count += 1
            
            # Update batch status
            batch.status = StipendBatchStatus.DISBURSED
            batch.save()
        
        return {
            'batch_id': batch.id,
            'status': batch.status,
            'disbursed_count': disbursed_count
        }
    
    @staticmethod
    def get_staff_stipend_history(staff_id: int, limit: int = 12) -> list:
        """
        Get disbursement history for a staff member.
        
        Returns last N months of disbursements.
        
        Args:
            staff_id: Staff ID (sid)
            limit: Number of months to return (default 12)
        
        Returns:
            list: Disbursement records with month, amount, status, payment_ref
        """
        try:
            staff = Staff.objects.get(sid=staff_id)
        except Staff.DoesNotExist:
            raise RSPCError(f"Staff {staff_id} not found")
        
        disbursements = StipendDisbursement.objects.filter(
            staff=staff
        ).order_by('-month')[:limit]
        
        return [
            {
                'month': d.month.strftime('%Y-%m'),
                'amount': float(d.stipend_amount),
                'status': d.status,
                'payment_reference': d.payment_reference or '',
                'payment_method': d.payment_method or '',
                'disbursement_date': d.disbursement_date.isoformat() if d.disbursement_date else None
            }
            for d in disbursements
        ]
    
    @staticmethod
    def calculate_stipend_amount(staff: Staff) -> Decimal:
        """
        Calculate stipend amount for a staff member.
        
        Gets stipend from staff.salary_per_month field.
        
        Args:
            staff: Staff instance
        
        Returns:
            Decimal: Stipend amount
        """
        return staff.salary_per_month or staff.salary
    
    @staticmethod
    def mark_disbursement_failed(disbursement_id: int, reason: str) -> dict:
        """
        Mark a disbursement as FAILED.
        
        Args:
            disbursement_id: Disbursement ID
            reason: Reason for failure
        
        Returns:
            dict: disbursement_id, status, reason
        
        Raises:
            RSPCError: If disbursement not found
        """
        try:
            disbursement = StipendDisbursement.objects.get(id=disbursement_id)
        except StipendDisbursement.DoesNotExist:
            raise RSPCError(f"Disbursement {disbursement_id} not found")
        
        with transaction.atomic():
            disbursement.status = StipendDisbursementStatus.FAILED
            disbursement.remarks = reason
            disbursement.save()
            
            # Trigger notification
            NotificationService.notify_stipend_failed(disbursement)
        
        return {
            'disbursement_id': disbursement.id,
            'status': disbursement.status,
            'reason': reason
        }

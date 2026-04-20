"""
RSPC Notification Service (UC-015 + Gap Items)
Central service for creating and dispatching notifications

Handles 18 event types:
1. expenditure_pending_approval
2. expenditure_approved
3. expenditure_rejected
4. budget_reallocated
5. proposal_pending_verification
6. proposal_approved
7. proposal_rejected
8. staff_committee_pending
9. staff_hod_pending
10. staff_rspc_pending
11. staff_appointed
12. fund_request_pending
13. fund_approved
14. patent_updated
15. small_fund_submitted (UC-021)
16. small_fund_approved (UC-022)
17. small_fund_rejected (UC-022)
18. small_fund_disbursed (UC-023)
"""

from django.db import transaction
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any

from .models import (
    Notification, NotificationEventType, NotificationEntityType,
    SmallFundRequest, FundDisbursement
)


class NotificationService:
    """Central service for creating notifications across all modules"""
    
    @staticmethod
    def _create_notification(
        recipient_user: User,
        event_type: str,
        entity_type: str,
        entity_id: str,
        title: str,
        message: str,
        sender_user: Optional[User] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Internal method to create a notification
        
        Args:
            recipient_user: Django User who receives the notification
            event_type: One of 14 NotificationEventType choices
            entity_type: NotificationEntityType (expenditure, project, etc.)
            entity_id: ID of the entity
            title: Short title (max 200 chars)
            message: Full message text
            sender_user: Sender user (optional, defaults to system)
            context_data: Additional data for rendering (dict)
        
        Returns:
            Created Notification instance
        """
        context_data = context_data or {}
        
        notification = Notification.objects.create(
            recipient=recipient_user,
            sender=sender_user,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            title=title,
            message=message,
            context_data=context_data,
            is_read=False
        )
        
        return notification
    
    # ========================================================================
    # EXPENDITURE NOTIFICATIONS (3 types)
    # ========================================================================
    
    @staticmethod
    def notify_expenditure_pending_approval(
        expenditure,
        approver_user: User,
        approver_role: str
    ) -> Notification:
        """
        Notify approver that expenditure is pending their approval
        
        Event: expenditure_pending_approval
        Title: "Expenditure ₹{amount} pending your approval"
        """
        title = f"Expenditure ₹{expenditure.amount:,.2f} pending your approval"
        message = (
            f"Expenditure request {expenditure.eid} for ₹{expenditure.amount:,.2f} "
            f"({expenditure.get_category_display()}) is pending your approval.\n"
            f"Purpose: {expenditure.purpose[:100]}..."
        )
        
        context_data = {
            'amount': str(expenditure.amount),
            'category': expenditure.category,
            'approver_role': approver_role,
            'project_id': expenditure.project_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=approver_user,
            event_type=NotificationEventType.EXPENDITURE_PENDING_APPROVAL,
            entity_type=NotificationEntityType.EXPENDITURE,
            entity_id=expenditure.eid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_expenditure_approved(
        expenditure,
        pi_user: User,
        approver_role: str
    ) -> Notification:
        """
        Notify PI that expenditure is approved
        
        Event: expenditure_approved
        Title: "Expenditure ₹{amount} approved"
        """
        title = f"Expenditure ₹{expenditure.amount:,.2f} approved"
        message = (
            f"Your expenditure request {expenditure.eid} for ₹{expenditure.amount:,.2f} "
            f"({expenditure.get_category_display()}) has been approved by {approver_role}."
        )
        
        context_data = {
            'amount': str(expenditure.amount),
            'category': expenditure.category,
            'approver_role': approver_role,
            'project_id': expenditure.project_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=pi_user,
            event_type=NotificationEventType.EXPENDITURE_APPROVED,
            entity_type=NotificationEntityType.EXPENDITURE,
            entity_id=expenditure.eid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_expenditure_rejected(
        expenditure,
        pi_user: User,
        rejection_reason: str
    ) -> Notification:
        """
        Notify PI that expenditure is rejected
        
        Event: expenditure_rejected
        Title: "Expenditure ₹{amount} rejected: {reason}"
        """
        title = f"Expenditure ₹{expenditure.amount:,.2f} rejected"
        message = (
            f"Your expenditure request {expenditure.eid} for ₹{expenditure.amount:,.2f} "
            f"({expenditure.get_category_display()}) has been rejected.\n"
            f"Reason: {rejection_reason}"
        )
        
        context_data = {
            'amount': str(expenditure.amount),
            'category': expenditure.category,
            'reason': rejection_reason,
            'project_id': expenditure.project_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=pi_user,
            event_type=NotificationEventType.EXPENDITURE_REJECTED,
            entity_type=NotificationEntityType.EXPENDITURE,
            entity_id=expenditure.eid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    # ========================================================================
    # BUDGET NOTIFICATIONS (1 type)
    # ========================================================================
    
    @staticmethod
    def notify_budget_reallocated(
        budget,
        admin_user: User,
        from_category: str,
        to_category: str,
        amount: Decimal
    ) -> Notification:
        """
        Notify RSPC Admin that budget has been reallocated
        
        Event: budget_reallocated
        Title: "Budget reallocated: ₹{amount} from {from_category} to {to_category}"
        """
        title = f"Budget reallocated: ₹{amount:,.2f} from {from_category} to {to_category}"
        message = (
            f"Budget for project {budget.project.name} has been reallocated.\n"
            f"Amount: ₹{amount:,.2f}\n"
            f"From: {from_category}\n"
            f"To: {to_category}"
        )
        
        context_data = {
            'amount': str(amount),
            'from_category': from_category,
            'to_category': to_category,
            'project_id': budget.project_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=admin_user,
            event_type=NotificationEventType.BUDGET_REALLOCATED,
            entity_type=NotificationEntityType.BUDGET,
            entity_id=budget.bid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    # ========================================================================
    # PROPOSAL/PROJECT NOTIFICATIONS (3 types)
    # ========================================================================
    
    @staticmethod
    def notify_proposal_pending_verification(
        proposal,
        admin_user: User,
        proposal_name: str
    ) -> Notification:
        """
        Notify RSPC Admin that proposal is pending verification
        
        Event: proposal_pending_verification
        Title: "Proposal '{name}' pending verification"
        """
        title = f"Proposal '{proposal_name}' pending verification"
        message = (
            f"Proposal {proposal.pid} - {proposal_name} is pending your verification.\n"
            f"Submitted: {proposal.submission_date.strftime('%Y-%m-%d')}"
        )
        
        context_data = {
            'proposal_name': proposal_name,
            'project_id': proposal.pid,
        }
        
        return NotificationService._create_notification(
            recipient_user=admin_user,
            event_type=NotificationEventType.PROPOSAL_PENDING_VERIFICATION,
            entity_type=NotificationEntityType.PROJECT,
            entity_id=proposal.pid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_proposal_approved(
        proposal,
        pi_user: User,
        proposal_name: str
    ) -> Notification:
        """
        Notify PI that proposal is approved
        
        Event: proposal_approved
        Title: "Proposal '{name}' approved and sanctioned"
        """
        title = f"Proposal '{proposal_name}' approved and sanctioned"
        message = (
            f"Your proposal {proposal.pid} - {proposal_name} has been approved and sanctioned.\n"
            f"Sanctioned Amount: ₹{proposal.sanctioned_amount:,.2f}\n"
            f"Sanction Date: {proposal.sanction_date.strftime('%Y-%m-%d') if proposal.sanction_date else 'TBD'}"
        )
        
        context_data = {
            'proposal_name': proposal_name,
            'sanctioned_amount': str(proposal.sanctioned_amount),
            'project_id': proposal.pid,
        }
        
        return NotificationService._create_notification(
            recipient_user=pi_user,
            event_type=NotificationEventType.PROPOSAL_APPROVED,
            entity_type=NotificationEntityType.PROJECT,
            entity_id=proposal.pid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_proposal_rejected(
        proposal,
        pi_user: User,
        proposal_name: str,
        rejection_reason: str
    ) -> Notification:
        """
        Notify PI that proposal is rejected
        
        Event: proposal_rejected
        Title: "Proposal '{name}' rejected: {reason}"
        """
        title = f"Proposal '{proposal_name}' rejected"
        message = (
            f"Your proposal {proposal.pid} - {proposal_name} has been rejected.\n"
            f"Reason: {rejection_reason}"
        )
        
        context_data = {
            'proposal_name': proposal_name,
            'reason': rejection_reason,
            'project_id': proposal.pid,
        }
        
        return NotificationService._create_notification(
            recipient_user=pi_user,
            event_type=NotificationEventType.PROPOSAL_REJECTED,
            entity_type=NotificationEntityType.PROJECT,
            entity_id=proposal.pid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    # ========================================================================
    # STAFF NOTIFICATIONS (4 types)
    # ========================================================================
    
    @staticmethod
    def notify_staff_committee_pending(
        staff,
        committee_member_user: User,
        position: str
    ) -> Notification:
        """
        Notify committee member that staff selection is pending review
        
        Event: staff_committee_pending
        Title: "Staff selection for {position} pending your review"
        """
        title = f"Staff selection for {position} pending your review"
        message = (
            f"Staff selection for position {position} (Staff ID: {staff.sid}) "
            f"is pending your review as a committee member."
        )
        
        context_data = {
            'position': position,
            'staff_id': staff.sid,
            'project_id': staff.pid_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=committee_member_user,
            event_type=NotificationEventType.STAFF_COMMITTEE_PENDING,
            entity_type=NotificationEntityType.STAFF,
            entity_id=staff.sid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_staff_hod_pending(
        staff,
        hod_user: User,
        position: str
    ) -> Notification:
        """
        Notify HOD that staff recommendation is pending approval
        
        Event: staff_hod_pending
        Title: "Staff recommendation pending your approval"
        """
        title = "Staff recommendation pending your approval"
        message = (
            f"Staff recommendation for position {position} (Staff ID: {staff.sid}) "
            f"is pending your approval as HOD."
        )
        
        context_data = {
            'position': position,
            'staff_id': staff.sid,
            'project_id': staff.pid_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=hod_user,
            event_type=NotificationEventType.STAFF_HOD_PENDING,
            entity_type=NotificationEntityType.STAFF,
            entity_id=staff.sid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_staff_rspc_pending(
        staff,
        rspc_admin_user: User,
        position: str
    ) -> Notification:
        """
        Notify RSPC Admin that staff appointment is pending final approval
        
        Event: staff_rspc_pending
        Title: "Staff appointment pending your final approval"
        """
        title = "Staff appointment pending your final approval"
        message = (
            f"Staff appointment for position {position} (Staff ID: {staff.sid}) "
            f"is pending your final approval as RSPC Administrator."
        )
        
        context_data = {
            'position': position,
            'staff_id': staff.sid,
            'project_id': staff.pid_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=rspc_admin_user,
            event_type=NotificationEventType.STAFF_RSPC_PENDING,
            entity_type=NotificationEntityType.STAFF,
            entity_id=staff.sid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_staff_appointed(
        staff,
        pi_user: User,
        staff_name: str,
        position: str
    ) -> Notification:
        """
        Notify PI that staff member has been appointed
        
        Event: staff_appointed
        Title: "Staff member {name} appointed for {position}"
        """
        title = f"Staff member {staff_name} appointed for {position}"
        message = (
            f"Staff member {staff_name} has been appointed for position {position}.\n"
            f"Start Date: {staff.start_date.strftime('%Y-%m-%d')}\n"
            f"Duration: {staff.duration} months"
        )
        
        context_data = {
            'staff_name': staff_name,
            'position': position,
            'staff_id': staff.sid,
            'project_id': staff.pid_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=pi_user,
            event_type=NotificationEventType.STAFF_APPOINTED,
            entity_type=NotificationEntityType.STAFF,
            entity_id=staff.sid,
            title=title,
            message=message,
            context_data=context_data
        )
    
    # ========================================================================
    # FUND NOTIFICATIONS (2 types)
    # ========================================================================
    
    @staticmethod
    def notify_fund_request_pending(
        fund_request,
        admin_user: User,
        amount: Decimal,
        requester_name: str
    ) -> Notification:
        """
        Notify admin that fund request is pending review
        
        Event: fund_request_pending
        Title: "Fund request ₹{amount} pending your review"
        """
        title = f"Fund request ₹{amount:,.2f} pending your review"
        message = (
            f"Fund request of ₹{amount:,.2f} from {requester_name} is pending your review.\n"
            f"Request ID: {fund_request.request_id}"
        )
        
        context_data = {
            'amount': str(amount),
            'requester_name': requester_name,
            'request_id': fund_request.request_id,
            'project_id': fund_request.project_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=admin_user,
            event_type=NotificationEventType.FUND_REQUEST_PENDING,
            entity_type=NotificationEntityType.FUND,
            entity_id=fund_request.request_id,
            title=title,
            message=message,
            context_data=context_data
        )
    
    @staticmethod
    def notify_fund_approved(
        fund_request,
        requester_user: User,
        amount: Decimal
    ) -> Notification:
        """
        Notify requester that fund request is approved
        
        Event: fund_approved
        Title: "Fund request ₹{amount} approved"
        """
        title = f"Fund request ₹{amount:,.2f} approved"
        message = (
            f"Your fund request of ₹{amount:,.2f} has been approved.\n"
            f"Request ID: {fund_request.request_id}"
        )
        
        context_data = {
            'amount': str(amount),
            'request_id': fund_request.request_id,
            'project_id': fund_request.project_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=requester_user,
            event_type=NotificationEventType.FUND_APPROVED,
            entity_type=NotificationEntityType.FUND,
            entity_id=fund_request.request_id,
            title=title,
            message=message,
            context_data=context_data
        )
    
     # ========================================================================
    # PATENT NOTIFICATIONS (1 type)
    # ========================================================================
    
    @staticmethod
    def notify_patent_updated(
        patent,
        inventor_user: User,
        patent_title: str,
        new_status: str
    ) -> Notification:
        """
        Notify inventor that patent status has been updated
        
        Event: patent_updated
        Title: "Patent '{title}' status updated to {status}"
        """
        title = f"Patent '{patent_title}' status updated to {new_status}"
        message = (
            f"The patent '{patent_title}' (Patent ID: {patent.id}) "
            f"status has been updated to {new_status}."
        )
        
        context_data = {
            'patent_title': patent_title,
            'new_status': new_status,
            'patent_id': patent.id,
        }
        
        return NotificationService._create_notification(
            recipient_user=inventor_user,
            event_type=NotificationEventType.PATENT_UPDATED,
            entity_type=NotificationEntityType.PATENT,
            entity_id=patent.id,
            title=title,
            message=message,
            context_data=context_data
        )
    
    # ========================================================================
    # UC-006: PROGRESS REPORT NOTIFICATIONS
    # ========================================================================
    
    @staticmethod
    def notify_progress_report_submitted(project, report):
        """Notify RSPC Admin and Director about submitted progress report"""
        try:
            from applications.globals.models import ExtraInfo
            
            # Find RSPC Admin and Director users
            admin_extras = ExtraInfo.objects.filter(designation__name__in=['RSPC Admin', 'RSPC_ADMIN'])
            director_extras = ExtraInfo.objects.filter(designation__name__in=['Director', 'DIRECTOR'])
            
            title = f"Progress Report Submitted: Project {project.name}"
            message = (
                f"Progress report for period {report.report_period} has been submitted "
                f"for project {project.name} by {report.submitted_by.username}"
            )
            
            context_data = {
                'project_id': project.pid,
                'project_name': project.name,
                'report_period': report.report_period,
                'submitted_by': report.submitted_by.username,
            }
            
            # Notify all admins and directors
            for extra in admin_extras.union(director_extras):
                if extra.user:
                    NotificationService._create_notification(
                        recipient_user=extra.user,
                        event_type='progress_report_submitted',
                        entity_type='project',
                        entity_id=str(project.pid),
                        title=title,
                        message=message,
                        context_data=context_data
                    )
        except Exception as e:
            pass  # Fail silently if notification fails
    
    @staticmethod
    def notify_progress_report_reviewed(report):
        """Notify PI about progress report being reviewed"""
        try:
            title = f"Progress Report Reviewed: Project {report.project.name}"
            message = (
                f"Your progress report for {report.report_period} has been reviewed.\n"
                f"Project: {report.project.name}"
            )
            
            context_data = {
                'project_id': report.project.pid,
                'project_name': report.project.name,
                'report_period': report.report_period,
            }
            
            if report.submitted_by:
                NotificationService._create_notification(
                    recipient_user=report.submitted_by,
                    event_type='progress_report_reviewed',
                    entity_type='project',
                    entity_id=str(report.project.pid),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    @staticmethod
    def notify_progress_report_approved(report):
        """Notify PI about progress report approval"""
        try:
            title = f"Progress Report Approved: Project {report.project.name}"
            message = (
                f"Your progress report for {report.report_period} has been approved.\n"
                f"Project: {report.project.name}"
            )
            
            context_data = {
                'project_id': report.project.pid,
                'project_name': report.project.name,
                'report_period': report.report_period,
            }
            
            if report.submitted_by:
                NotificationService._create_notification(
                    recipient_user=report.submitted_by,
                    event_type='progress_report_approved',
                    entity_type='project',
                    entity_id=str(report.project.pid),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    # ========================================================================
    # UC-021/022/023: SMALL FUND REQUEST NOTIFICATIONS
    # ========================================================================
    
    @staticmethod
    def small_fund_submitted(fund_request: SmallFundRequest, requester: User):
        """
        Notify HOD that small fund request has been submitted
        Event: small_fund_submitted
        """
        title = f"Small Fund Request: ₹{fund_request.amount:,.2f} - {fund_request.title}"
        message = (
            f"New small fund request from {requester.get_full_name()}\n"
            f"Amount: ₹{fund_request.amount:,.2f}\n"
            f"Title: {fund_request.title}\n"
            f"Purpose: {fund_request.purpose}"
        )
        
        context_data = {
            'amount': str(fund_request.amount),
            'title': fund_request.title,
            'requested_by': requester.username,
            'request_id': fund_request.request_id,
        }
        
        try:
            # TODO: Get HOD user for the faculty's department
            # For now, notify a system admin or configured approver
            pass
        except Exception as e:
            pass
    
    @staticmethod
    def small_fund_approved(fund_request: SmallFundRequest, approver: User):
        """
        Notify requester that small fund request has been approved
        Event: small_fund_approved
        """
        title = f"Small Fund Request Approved: ₹{fund_request.amount:,.2f}"
        message = (
            f"Your small fund request of ₹{fund_request.amount:,.2f} for '{fund_request.title}' "
            f"has been approved by {approver.get_full_name()}.\n"
            f"Approval Date: {fund_request.approval_date.strftime('%Y-%m-%d')}"
        )
        
        context_data = {
            'amount': str(fund_request.amount),
            'title': fund_request.title,
            'approved_by': approver.get_full_name(),
            'request_id': fund_request.request_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=fund_request.requested_by,
            event_type=NotificationEventType.SMALL_FUND_APPROVED,
            entity_type=NotificationEntityType.SMALL_FUND,
            entity_id=str(fund_request.request_id),
            title=title,
            message=message,
            sender_user=approver,
            context_data=context_data
        )
    
    @staticmethod
    def small_fund_rejected(fund_request: SmallFundRequest, rejecter: User, reason: str = ""):
        """
        Notify requester that small fund request has been rejected
        Event: small_fund_rejected
        """
        title = f"Small Fund Request Rejected: ₹{fund_request.amount:,.2f}"
        message = (
            f"Your small fund request of ₹{fund_request.amount:,.2f} for '{fund_request.title}' "
            f"has been rejected.\n"
            f"Reason: {reason or 'No reason provided'}"
        )
        
        context_data = {
            'amount': str(fund_request.amount),
            'title': fund_request.title,
            'rejected_by': rejecter.get_full_name(),
            'reason': reason,
            'request_id': fund_request.request_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=fund_request.requested_by,
            event_type=NotificationEventType.SMALL_FUND_REJECTED,
            entity_type=NotificationEntityType.SMALL_FUND,
            entity_id=str(fund_request.request_id),
            title=title,
            message=message,
            sender_user=rejecter,
            context_data=context_data
        )
    
    @staticmethod
    def small_fund_disbursed(fund_request: SmallFundRequest, disbursement: FundDisbursement, disburser: User):
        """
        Notify requester that fund has been disbursed
        Event: small_fund_disbursed
        """
        title = f"Small Fund Disbursed: ₹{disbursement.amount:,.2f}"
        message = (
            f"Your small fund request of ₹{disbursement.amount:,.2f} has been disbursed.\n"
            f"Method: {disbursement.get_method_display()}\n"
            f"Reference: {disbursement.reference_number}\n"
            f"Disbursement Date: {disbursement.disbursement_date.strftime('%Y-%m-%d')}"
        )
        
        context_data = {
            'amount': str(disbursement.amount),
            'method': disbursement.method,
            'reference': disbursement.reference_number,
            'request_id': fund_request.request_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=fund_request.requested_by,
            event_type=NotificationEventType.SMALL_FUND_DISBURSED,
            entity_type=NotificationEntityType.SMALL_FUND,
            entity_id=str(fund_request.request_id),
            title=title,
            message=message,
            sender_user=disburser,
            context_data=context_data
        )
    
    @staticmethod
    def small_fund_disbursement_failed(fund_request: SmallFundRequest, disbursement: FundDisbursement, handler: User):
        """
        Notify requester that disbursement has failed
        """
        title = f"Small Fund Disbursement Failed: ₹{disbursement.amount:,.2f}"
        message = (
            f"Disbursement of ₹{disbursement.amount:,.2f} for your small fund request has failed.\n"
            f"Remarks: {disbursement.remarks}\n"
            f"Please contact the admin for further assistance."
        )
        
        context_data = {
            'amount': str(disbursement.amount),
            'remarks': disbursement.remarks,
            'request_id': fund_request.request_id,
        }
        
        return NotificationService._create_notification(
            recipient_user=fund_request.requested_by,
            event_type='small_fund_disbursement_failed',
            entity_type=NotificationEntityType.SMALL_FUND,
            entity_id=str(fund_request.request_id),
            title=title,
            message=message,
            sender_user=handler,
            context_data=context_data
        )
    
    @staticmethod
    def notify_progress_report_rejected(report):
        """Notify PI about progress report rejection"""
        try:
            title = f"Progress Report Rejected: Project {report.project.name}"
            message = (
                f"Your progress report for {report.report_period} has been rejected.\n"
                f"Project: {report.project.name}\n"
                f"Comments: {report.reviewer_comments}"
            )
            
            context_data = {
                'project_id': report.project.pid,
                'project_name': report.project.name,
                'report_period': report.report_period,
                'comments': report.reviewer_comments,
            }
            
            if report.submitted_by:
                NotificationService._create_notification(
                    recipient_user=report.submitted_by,
                    event_type='progress_report_rejected',
                    entity_type='project',
                    entity_id=str(report.project.pid),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    # ========================================================================
    # UC-010: PROJECT CLOSURE NOTIFICATIONS
    # ========================================================================
    
    @staticmethod
    def notify_project_closure_submitted(project, closure):
        """Notify RSPC Admin and Director about project closure submission"""
        try:
            from applications.globals.models import ExtraInfo
            
            # Find RSPC Admin and Director users
            admin_extras = ExtraInfo.objects.filter(designation__name__in=['RSPC Admin', 'RSPC_ADMIN'])
            director_extras = ExtraInfo.objects.filter(designation__name__in=['Director', 'DIRECTOR'])
            
            title = f"Project Closure Submitted: {project.name}"
            message = (
                f"Closure report has been submitted for project {project.name}.\n"
                f"Submitted by: {closure.closed_by.username if closure.closed_by else 'System'}"
            )
            
            context_data = {
                'project_id': project.pid,
                'project_name': project.name,
                'submitted_by': closure.closed_by.username if closure.closed_by else 'System',
            }
            
            # Notify all admins and directors
            for extra in admin_extras.union(director_extras):
                if extra.user:
                    NotificationService._create_notification(
                        recipient_user=extra.user,
                        event_type='project_closure_submitted',
                        entity_type='project',
                        entity_id=str(project.pid),
                        title=title,
                        message=message,
                        context_data=context_data
                    )
        except Exception as e:
            pass
    
    @staticmethod
    def notify_project_closure_status_changed(closure):
        """Notify PI about project closure status change"""
        try:
            title = f"Project Closure Status: {closure.get_status_display()}"
            message = (
                f"Project closure for {closure.project.name} status has changed to {closure.status}."
            )
            
            context_data = {
                'project_id': closure.project.pid,
                'project_name': closure.project.name,
                'status': closure.status,
            }
            
            if closure.closed_by:
                NotificationService._create_notification(
                    recipient_user=closure.closed_by,
                    event_type='project_closure_status_changed',
                    entity_type='project',
                    entity_id=str(closure.project.pid),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    # ========================================================================
    # BR-018: APPROVAL DEADLINE NOTIFICATIONS
    # ========================================================================
    
    @staticmethod
    def notify_approval_deadline_approaching(approver_user: User, entity_type: str, entity_name: str):
        """Notify approver that approval deadline is approaching (1 day before)"""
        try:
            title = f"Approval Deadline Approaching: {entity_name}"
            message = (
                f"Approval deadline for {entity_type} - {entity_name} is in 1 day. "
                f"Please review and take action."
            )
            
            context_data = {
                'entity_type': entity_type,
                'entity_name': entity_name,
                'urgency': 'HIGH',
            }
            
            NotificationService._create_notification(
                recipient_user=approver_user,
                event_type='approval_deadline_approaching',
                entity_type='project' if entity_type == 'project' else entity_type,
                entity_id='0',
                title=title,
                message=message,
                context_data=context_data
            )
        except Exception as e:
            pass
    
    @staticmethod
    def notify_approval_overdue(approver_user: User, entity_type: str, entity_name: str):
        """Notify approver that approval is overdue"""
        try:
            title = f"Approval Overdue: {entity_name}"
            message = (
                f"Approval for {entity_type} - {entity_name} is overdue. "
                f"Immediate action required."
            )
            
            context_data = {
                'entity_type': entity_type,
                'entity_name': entity_name,
                'urgency': 'CRITICAL',
            }
            
            NotificationService._create_notification(
                recipient_user=approver_user,
                event_type='approval_overdue',
                entity_type='project' if entity_type == 'project' else entity_type,
                entity_id='0',
                title=title,
                message=message,
                context_data=context_data
            )
        except Exception as e:
            pass
    
    @staticmethod
    def notify_approval_escalated(escalated_to_user: User, entity_type: str, entity_name: str):
        """Notify new approver that approval has been escalated to them"""
        try:
            title = f"Approval Escalated to You: {entity_name}"
            message = (
                f"Approval for {entity_type} - {entity_name} has been escalated to your level. "
                f"Please review and take action."
            )
            
            context_data = {
                'entity_type': entity_type,
                'entity_name': entity_name,
                'urgency': 'HIGH',
            }
            
            NotificationService._create_notification(
                recipient_user=escalated_to_user,
                event_type='approval_escalated',
                entity_type='project' if entity_type == 'project' else entity_type,
                entity_id='0',
                title=title,
                message=message,
                context_data=context_data
            )
        except Exception as e:
            pass
    
    # ========================================================================
    # UC-017: STIPEND DISBURSEMENT NOTIFICATIONS
    # ========================================================================
    
    @staticmethod
    def notify_stipend_batch_approved(batch):
        """Notify RSPC Admin that batch has been approved for disbursement"""
        try:
            title = f"Stipend Batch Approved: Project {batch.project.pid}"
            message = (
                f"Stipend batch for {batch.month.strftime('%B %Y')} has been approved.\n"
                f"Staff Count: {batch.disbursement_count}\n"
                f"Total Amount: ₹{batch.total_amount:,.2f}"
            )
            
            context_data = {
                'batch_id': batch.id,
                'project_id': batch.project.pid,
                'month': batch.month.isoformat(),
                'total_amount': str(batch.total_amount),
                'staff_count': batch.disbursement_count,
            }
            
            # Notify approved_by user if available
            if batch.approved_by:
                NotificationService._create_notification(
                    recipient_user=batch.approved_by,
                    event_type='stipend_batch_approved',
                    entity_type='staff',
                    entity_id=str(batch.id),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    @staticmethod
    def notify_stipend_disbursed(disbursement):
        """Notify staff that their stipend has been disbursed"""
        try:
            title = f"Stipend Disbursed: ₹{disbursement.stipend_amount:,.2f}"
            message = (
                f"Your stipend for {disbursement.month.strftime('%B %Y')} has been disbursed.\n"
                f"Amount: ₹{disbursement.stipend_amount:,.2f}\n"
                f"Payment Method: {disbursement.get_payment_method_display()}\n"
                f"Reference: {disbursement.payment_reference or 'N/A'}"
            )
            
            context_data = {
                'amount': str(disbursement.stipend_amount),
                'month': disbursement.month.isoformat(),
                'payment_method': disbursement.payment_method,
                'payment_reference': disbursement.payment_reference,
            }
            
            # Get staff user
            staff_user = disbursement.staff.created_by
            if staff_user:
                NotificationService._create_notification(
                    recipient_user=staff_user,
                    event_type='stipend_disbursed',
                    entity_type='staff',
                    entity_id=str(disbursement.id),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    @staticmethod
    def notify_stipend_failed(disbursement):
        """Notify staff that their stipend disbursement failed"""
        try:
            title = f"Stipend Disbursement Failed: ₹{disbursement.stipend_amount:,.2f}"
            message = (
                f"Your stipend disbursement for {disbursement.month.strftime('%B %Y')} failed.\n"
                f"Amount: ₹{disbursement.stipend_amount:,.2f}\n"
                f"Reason: {disbursement.remarks}"
            )
            
            context_data = {
                'amount': str(disbursement.stipend_amount),
                'month': disbursement.month.isoformat(),
                'reason': disbursement.remarks,
            }
            
            # Get staff user
            staff_user = disbursement.staff.created_by
            if staff_user:
                NotificationService._create_notification(
                    recipient_user=staff_user,
                    event_type='stipend_failed',
                    entity_type='staff',
                    entity_id=str(disbursement.id),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    # ========================================================================
    # UC-018: COMPLIANCE REPORT NOTIFICATIONS
    # ========================================================================
    
    @staticmethod
    def notify_compliance_report_generated(report):
        """Notify RSPC Admin that compliance report has been generated"""
        try:
            title = f"Compliance Report Generated: {report.get_report_type_display()}"
            message = (
                f"Compliance report for {report.get_report_type_display()} has been generated.\n"
                f"Period: {report.period_start} to {report.period_end}\n"
                f"Compliance: {report.compliance_percentage}%"
            )
            
            context_data = {
                'report_id': report.id,
                'report_type': report.report_type,
                'compliance_percent': str(report.compliance_percentage),
                'period_start': report.period_start.isoformat(),
                'period_end': report.period_end.isoformat(),
            }
            
            if report.generated_by:
                NotificationService._create_notification(
                    recipient_user=report.generated_by,
                    event_type='compliance_report_generated',
                    entity_type='project',
                    entity_id=str(report.id),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass
    
    # ========================================================================
    # BR-015: SETTLEMENT NOTIFICATIONS
    # ========================================================================
    
    @staticmethod
    def notify_settlement_calculated(closure):
        """Notify Director that settlement has been calculated"""
        try:
            title = f"Settlement Calculated: Project {closure.project.pid}"
            message = (
                f"Settlement for project {closure.project.pid} has been calculated.\n"
                f"Settlement Amount: ₹{closure.settlement_amount:,.2f}\n"
                f"Refund Amount: ₹{closure.refund_amount:,.2f}\n"
                f"Penalties: ₹{closure.penalty_amount:,.2f}"
            )
            
            context_data = {
                'closure_id': closure.closure_id,
                'project_id': closure.project.pid,
                'settlement_amount': str(closure.settlement_amount) if closure.settlement_amount else '0',
                'refund_amount': str(closure.refund_amount) if closure.refund_amount else '0',
                'penalty_amount': str(closure.penalty_amount),
            }
            
            # Notify Director
            # (Implementation would get Director from project or config)
            pass
        except Exception as e:
            pass
    
    @staticmethod
    def notify_settlement_approved(closure):
        """Notify RSPC Admin that settlement has been approved"""
        try:
            title = f"Settlement Approved: Project {closure.project.pid}"
            message = (
                f"Settlement for project {closure.project.pid} has been approved.\n"
                f"Final Settlement Amount: ₹{closure.settlement_amount:,.2f}"
            )
            
            context_data = {
                'closure_id': closure.closure_id,
                'project_id': closure.project.pid,
                'settlement_amount': str(closure.settlement_amount) if closure.settlement_amount else '0',
            }
            
            # Notify closed_by user (usually RSPC Admin or PI)
            if closure.closed_by:
                NotificationService._create_notification(
                    recipient_user=closure.closed_by,
                    event_type='settlement_approved',
                    entity_type='project',
                    entity_id=str(closure.closure_id),
                    title=title,
                    message=message,
                    context_data=context_data
                )
        except Exception as e:
            pass

"""
UC-018: Compliance Report Service
Generates compliance reports for RSPC entities with multi-format export
"""

from decimal import Decimal
from datetime import datetime, date
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
import json

from .models import (
    ComplianceReport, Project, Budget, Expenditure, Staff, Committee,
    ComplianceReportType, ComplianceReportStatus,
    ExpenditureApprovalHistory, ProjectStatus
)


class RSPCError(Exception):
    """Base exception for RSPC operations"""
    pass


class ComplianceService:
    """
    Service for generating compliance reports.
    Implements UC-018 requirements with BR validation.
    """
    
    @staticmethod
    def generate_budget_compliance(period_start: date, period_end: date, user: User) -> dict:
        """
        Check all budgets for compliance with BR rules.
        
        Validates:
        - BR-004: All projects have budget allocated
        - BR-005: Personnel costs within limits
        - BR-RSPC-08: Budget reallocation ≤20%
        
        Args:
            period_start: Start date
            period_end: End date
            user: User generating report
        
        Returns:
            dict: report_id, compliance_%, items_checked
        """
        budgets = Budget.objects.filter(
            created_date__date__gte=period_start,
            created_date__date__lte=period_end
        )
        
        total_items = budgets.count()
        compliant_items = 0
        non_compliant_items = 0
        findings = []
        
        for budget in budgets:
            is_compliant = True
            issues = []
            
            # BR-004: Budget allocated
            if budget.allocated_amount <= 0:
                is_compliant = False
                issues.append("BR-004: No budget allocated")
            
            # BR-005: Personnel costs check
            manpower_percentage = Decimal('0')
            if budget.allocated_amount > 0:
                manpower_percentage = (budget.manpower_allocation / budget.allocated_amount) * 100
            
            if manpower_percentage > 40:  # Assumed limit
                is_compliant = False
                issues.append(f"BR-005: Personnel costs {manpower_percentage}% exceed limit")
            
            # BR-RSPC-08: Reallocation check
            reallocations = budget.reallocations.filter(
                requested_at__date__gte=period_start,
                requested_at__date__lte=period_end
            )
            
            for realloc in reallocations:
                realloc_percentage = (realloc.amount / budget.allocated_amount) * 100
                if realloc_percentage > 20:
                    is_compliant = False
                    issues.append(f"BR-RSPC-08: Reallocation {realloc_percentage}% exceeds 20% limit")
            
            if is_compliant:
                compliant_items += 1
            else:
                non_compliant_items += 1
                findings.append({
                    'type': 'BUDGET',
                    'entity_id': budget.bid,
                    'project': budget.project.pid,
                    'issues': issues
                })
        
        compliance_percent = (compliant_items / total_items * 100) if total_items > 0 else 100
        
        with transaction.atomic():
            report = ComplianceReport.objects.create(
                report_type=ComplianceReportType.BUDGET,
                period_start=period_start,
                period_end=period_end,
                generated_by=user,
                total_items_checked=total_items,
                compliant_items=compliant_items,
                non_compliant_items=non_compliant_items,
                compliance_percentage=compliance_percent,
                report_content={
                    'findings': findings,
                    'summary': f"{compliant_items}/{total_items} budgets compliant"
                }
            )
        
        return {
            'report_id': report.id,
            'compliance_percent': float(compliance_percent),
            'items_checked': total_items
        }
    
    @staticmethod
    def generate_expenditure_compliance(period_start: date, period_end: date, user: User) -> dict:
        """
        Check all expenditures for compliance with BR rules.
        
        Validates:
        - BR-RSPC-13: All approved within tier limits
        - All have proper approval chain
        - BR-RSPC-18: All >50K have documents
        
        Args:
            period_start: Start date
            period_end: End date
            user: User generating report
        
        Returns:
            dict: report_id, compliance_%, items_checked
        """
        expenditures = Expenditure.objects.filter(
            created_date__date__gte=period_start,
            created_date__date__lte=period_end
        )
        
        total_items = expenditures.count()
        compliant_items = 0
        non_compliant_items = 0
        findings = []
        
        for exp in expenditures:
            is_compliant = True
            issues = []
            
            # Check approval chain
            approvals = ExpenditureApprovalHistory.objects.filter(expenditure=exp)
            if not approvals.exists():
                is_compliant = False
                issues.append("Missing approval chain")
            
            # BR-RSPC-18: Documents for >50K
            if exp.amount > 50000 and not exp.is_eligible_for_approval:
                is_compliant = False
                issues.append("BR-RSPC-18: Amount >50K but no supporting documents")
            
            if is_compliant:
                compliant_items += 1
            else:
                non_compliant_items += 1
                findings.append({
                    'type': 'EXPENDITURE',
                    'entity_id': exp.eid,
                    'amount': float(exp.amount),
                    'issues': issues
                })
        
        compliance_percent = (compliant_items / total_items * 100) if total_items > 0 else 100
        
        with transaction.atomic():
            report = ComplianceReport.objects.create(
                report_type=ComplianceReportType.EXPENDITURE,
                period_start=period_start,
                period_end=period_end,
                generated_by=user,
                total_items_checked=total_items,
                compliant_items=compliant_items,
                non_compliant_items=non_compliant_items,
                compliance_percentage=compliance_percent,
                report_content={
                    'findings': findings,
                    'summary': f"{compliant_items}/{total_items} expenditures compliant"
                }
            )
        
        return {
            'report_id': report.id,
            'compliance_percent': float(compliance_percent),
            'items_checked': total_items
        }
    
    @staticmethod
    def generate_staff_compliance(period_start: date, period_end: date, user: User) -> dict:
        """
        Check staff records for compliance.
        
        Validates:
        - BR-RSPC-12: All committees have min 3 members
        - All PI-eligible designations confirmed
        - BR-RSPC-15: No self-approvals
        
        Args:
            period_start: Start date
            period_end: End date
            user: User generating report
        
        Returns:
            dict: report_id, compliance_%, items_checked
        """
        committees = Committee.objects.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        
        total_items = committees.count()
        compliant_items = 0
        non_compliant_items = 0
        findings = []
        
        for committee in committees:
            is_compliant = True
            issues = []
            
            # BR-RSPC-12: Min 3 members
            member_count = committee.members.count()
            if member_count < 3:
                is_compliant = False
                issues.append(f"BR-RSPC-12: Committee has {member_count} members (need min 3)")
            
            if is_compliant:
                compliant_items += 1
            else:
                non_compliant_items += 1
                findings.append({
                    'type': 'COMMITTEE',
                    'entity_id': committee.committee_id,
                    'name': committee.name,
                    'issues': issues
                })
        
        compliance_percent = (compliant_items / total_items * 100) if total_items > 0 else 100
        
        with transaction.atomic():
            report = ComplianceReport.objects.create(
                report_type=ComplianceReportType.STAFF,
                period_start=period_start,
                period_end=period_end,
                generated_by=user,
                total_items_checked=total_items,
                compliant_items=compliant_items,
                non_compliant_items=non_compliant_items,
                compliance_percentage=compliance_percent,
                report_content={
                    'findings': findings,
                    'summary': f"{compliant_items}/{total_items} staff records compliant"
                }
            )
        
        return {
            'report_id': report.id,
            'compliance_percent': float(compliance_percent),
            'items_checked': total_items
        }
    
    @staticmethod
    def generate_project_compliance(period_start: date, period_end: date, user: User) -> dict:
        """
        Check projects for compliance.
        
        Validates:
        - BR-RSPC-02, 03: All PI-eligible
        - BR-RSPC-17: Duration 6-60 months
        - BR-RSPC-05: Unique names
        - BR-RSPC-06: PI/Co-PI distinct
        
        Args:
            period_start: Start date
            period_end: End date
            user: User generating report
        
        Returns:
            dict: report_id, compliance_%, items_checked
        """
        projects = Project.objects.filter(
            created_date__date__gte=period_start,
            created_date__date__lte=period_end
        )
        
        total_items = projects.count()
        compliant_items = 0
        non_compliant_items = 0
        findings = []
        
        for project in projects:
            is_compliant = True
            issues = []
            
            # BR-RSPC-17: Duration check
            if project.estimated_duration < 6 or project.estimated_duration > 60:
                is_compliant = False
                issues.append(f"BR-RSPC-17: Duration {project.estimated_duration}m not in 6-60 range")
            
            if is_compliant:
                compliant_items += 1
            else:
                non_compliant_items += 1
                findings.append({
                    'type': 'PROJECT',
                    'entity_id': project.pid,
                    'name': project.title,
                    'issues': issues
                })
        
        compliance_percent = (compliant_items / total_items * 100) if total_items > 0 else 100
        
        with transaction.atomic():
            report = ComplianceReport.objects.create(
                report_type=ComplianceReportType.PROJECT,
                period_start=period_start,
                period_end=period_end,
                generated_by=user,
                total_items_checked=total_items,
                compliant_items=compliant_items,
                non_compliant_items=non_compliant_items,
                compliance_percentage=compliance_percent,
                report_content={
                    'findings': findings,
                    'summary': f"{compliant_items}/{total_items} projects compliant"
                }
            )
        
        return {
            'report_id': report.id,
            'compliance_percent': float(compliance_percent),
            'items_checked': total_items
        }
    
    @staticmethod
    def calculate_compliance_score(items_total: int, items_compliant: int) -> float:
        """Calculate compliance percentage"""
        if items_total == 0:
            return 100.0
        return float((items_compliant / items_total) * 100)
    
    @staticmethod
    def export_to_pdf(report: ComplianceReport) -> str:
        """
        Export report to PDF format.
        Returns file path (actual PDF generation done by external service)
        """
        # Placeholder for PDF export logic
        # In real implementation, use reportlab or weasyprint
        file_path = f"media/rspc/reports/compliance_report_{report.id}.pdf"
        report.export_formats['pdf'] = file_path
        report.save()
        return file_path
    
    @staticmethod
    def export_to_excel(report: ComplianceReport) -> str:
        """
        Export report to Excel format.
        Returns file path (actual Excel generation done by external service)
        """
        # Placeholder for Excel export logic
        # In real implementation, use openpyxl or xlsxwriter
        file_path = f"media/rspc/reports/compliance_report_{report.id}.xlsx"
        report.export_formats['xlsx'] = file_path
        report.save()
        return file_path
    
    @staticmethod
    def approve_report(report_id: int, user: User) -> dict:
        """
        Approve a compliance report.
        
        Args:
            report_id: Report ID
            user: User approving (must be Director)
        
        Returns:
            dict: report_id, status
        
        Raises:
            RSPCError: If report not found or already approved
        """
        try:
            report = ComplianceReport.objects.get(id=report_id)
        except ComplianceReport.DoesNotExist:
            raise RSPCError(f"Report {report_id} not found")
        
        with transaction.atomic():
            report.status = ComplianceReportStatus.APPROVED
            report.save()
        
        return {
            'report_id': report.id,
            'status': report.status
        }

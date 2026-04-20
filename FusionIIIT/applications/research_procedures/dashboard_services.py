"""
RSPC Dashboard Service - Role-Based Dashboard Data Generation
Implements Part 2: Dashboard with real data integration
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, F
from django.contrib.auth.models import User

from .models import (
    Project, Budget, Staff, Expenditure, Request,
    Notification, SponsoredProject, ProjectExpenditure,
    StaffApprovalStatus, RequestStatus
)
from applications.globals.models import ExtraInfo, Faculty, HoldsDesignation, Designation
from .role_filters import get_user_roles, get_faculty_by_username, get_user_department


class DashboardService:
    """
    Generates role-specific dashboard data
    Different roles see different information per BR-RSPC specifications
    """
    
    # Role-specific data visibility constants
    PENDING_APPROVAL_RANGE_HOD = (50000, 200000)  # 50K-200K for HOD
    PENDING_APPROVAL_RANGE_DEAN = (200000, float('inf'))  # >200K for Dean
    
    @classmethod
    def get_dashboard(cls, request):
        """
        Main entry point: Generate role-specific dashboard data
        Returns dict with role and all required data sections
        """
        username = request.user.username
        roles = get_user_roles(username)
        
        # Determine primary role (priority: rspc_admin > dean_rspc > hod > pi)
        if roles['rspc_admin']:
            primary_role = 'rspc_admin'
        elif roles['dean_rspc']:
            primary_role = 'dean_rspc'
        elif roles['hod']:
            primary_role = 'hod'
        elif roles['pi']:
            primary_role = 'pi'
        elif roles['committee']:
            primary_role = 'committee'
        elif roles['director']:
            primary_role = 'director'
        else:
            primary_role = 'guest'
        
        # Get base dashboard structure
        dashboard = {
            'role': primary_role,
            'user': request.user.get_full_name() or request.user.username,
        }
        
        # Add role-specific data
        if primary_role == 'pi':
            dashboard.update(cls._get_pi_dashboard(username))
        elif primary_role == 'hod':
            dashboard.update(cls._get_hod_dashboard(username))
        elif primary_role == 'dean_rspc':
            dashboard.update(cls._get_dean_dashboard(username))
        elif primary_role == 'director':
            dashboard.update(cls._get_director_dashboard(username))
        elif primary_role == 'rspc_admin':
            dashboard.update(cls._get_admin_dashboard(username))
        elif primary_role == 'committee':
            dashboard.update(cls._get_committee_dashboard(username))
        else:
            dashboard.update(cls._get_guest_dashboard())
        
        # Add common data
        dashboard['notifications_unread'] = cls._get_unread_notifications(username)
        dashboard['recent_notifications'] = cls._get_recent_notifications(username, limit=5)
        
        return dashboard
    
    # ========================================================================
    # PI DASHBOARD
    # ========================================================================
    
    @classmethod
    def _get_pi_dashboard(cls, username):
        """
        PI sees: Own projects, expenditures awaiting approval, staff requests, budget utilization
        """
        faculty = get_faculty_by_username(username)
        if not faculty:
            return {}
        
        # Own projects
        projects = Project.objects.filter(pi_id=faculty.id)
        
        # Pending expenditures awaiting PI approval
        pending_approvals = Expenditure.objects.filter(
            project__in=projects,
            status__in=['pending_pi', 'pending']
        ).count()
        
        # Pending staff requests
        pending_staff = Staff.objects.filter(
            project__in=projects,
            status='pending'
        ).count()
        
        # Pending proposals (research proposals)
        pending_proposals = Project.objects.filter(
            pi_id=faculty.id,
            status='PROPOSED'
        ).count()
        
        # Budget summary
        budgets = Budget.objects.filter(project__in=projects)
        total_allocated = budgets.aggregate(Sum('total_sanctioned'))['total_sanctioned__sum'] or 0
        utilized = budgets.aggregate(Sum('current_funds'))['current_funds__sum'] or 0
        remaining = total_allocated - utilized if total_allocated > 0 else 0
        
        alerts = []
        if total_allocated > 0:
            utilization_pct = (utilized / total_allocated) * 100
            if utilization_pct > 80:
                alerts.append(f"High utilization: {utilization_pct:.1f}%")
        
        return {
            'pending_items': {
                'pending_approvals': pending_approvals,
                'pending_staff': pending_staff,
                'pending_proposals': pending_proposals,
            },
            'recent_projects': cls._get_recent_projects(projects, limit=5),
            'budget_summary': {
                'total_allocated': float(total_allocated),
                'utilized': float(utilized),
                'remaining': float(remaining),
                'alerts': alerts,
            },
            'quick_stats': {
                'total_projects': projects.count(),
                'ongoing_projects': projects.filter(status='ONGOING').count(),
                'completed_projects': projects.filter(status='COMPLETED').count(),
                'pending_expenditures': pending_approvals,
                'pending_proposals': pending_proposals,
                'pending_staff': pending_staff,
            }
        }
    
    # ========================================================================
    # HOD DASHBOARD
    # ========================================================================
    
    @classmethod
    def _get_hod_dashboard(cls, username):
        """
        HOD sees: Department projects, expenditure approvals (50-200K), staff recommendations, 
        department budget summary
        """
        department_id = get_user_department(username)
        faculty = get_faculty_by_username(username)
        if not department_id:
            return {}
        
        # Department projects (where PI or Co-PI is in department)
        dept_projects = Project.objects.filter(
            Q(dept=str(department_id)) |
            Q(pi_id__in=Faculty.objects.filter(department_id=department_id).values_list('id', flat=True))
        )
        
        # Expenditures in 50-200K range pending HOD approval
        pending_approvals = Expenditure.objects.filter(
            project__in=dept_projects,
            amount__gt=50000,
            amount__lte=200000,
            status='pending_hod'
        ).count()
        
        # Staff requests pending HOD recommendation
        pending_staff = Staff.objects.filter(
            project__in=dept_projects,
            status=StaffApprovalStatus.HOD_PENDING
        ).count()
        
        # Budget summary for department
        budgets = Budget.objects.filter(project__in=dept_projects)
        total_allocated = budgets.aggregate(Sum('total_sanctioned'))['total_sanctioned__sum'] or 0
        utilized = budgets.aggregate(Sum('current_funds'))['current_funds__sum'] or 0
        remaining = total_allocated - utilized if total_allocated > 0 else 0
        
        alerts = []
        if total_allocated > 0:
            utilization_pct = (utilized / total_allocated) * 100
            if utilization_pct > 80:
                alerts.append(f"Department utilization: {utilization_pct:.1f}%")
        
        return {
            'pending_items': {
                'pending_approvals': pending_approvals,
                'pending_reviews': pending_staff,
            },
            'recent_projects': cls._get_recent_projects(dept_projects, limit=5),
            'budget_summary': {
                'total_allocated': float(total_allocated),
                'utilized': float(utilized),
                'remaining': float(remaining),
                'alerts': alerts,
            },
            'quick_stats': {
                'total_projects': dept_projects.count(),
                'ongoing_projects': dept_projects.filter(status='ONGOING').count(),
                'completed_projects': dept_projects.filter(status='COMPLETED').count(),
                'pending_expenditures': pending_approvals,
                'pending_staff': pending_staff,
            }
        }
    
    # ========================================================================
    # DEAN RSPC DASHBOARD
    # ========================================================================
    
    @classmethod
    def _get_dean_dashboard(cls, username):
        """
        Dean RSPC sees: All pending proposals, high-value expenditures (>200K), 
        fund requests pending, institute-wide stats
        """
        # All projects (global view)
        all_projects = Project.objects.all()
        
        # Pending proposals awaiting Dean approval
        pending_proposals = all_projects.filter(status='PROPOSED').count()
        
        # High-value expenditures >200K pending approval
        pending_expenditures = Expenditure.objects.filter(
            amount__gt=200000,
            status='pending_dean'
        ).count()
        
        # Fund requests pending Dean approval
        pending_requests = Request.objects.filter(
            request_type='funds',
            status=RequestStatus.PENDING
        ).count()
        
        # Institute budget summary
        budgets = Budget.objects.all()
        total_allocated = budgets.aggregate(Sum('total_sanctioned'))['total_sanctioned__sum'] or 0
        utilized = budgets.aggregate(Sum('current_funds'))['current_funds__sum'] or 0
        remaining = total_allocated - utilized if total_allocated > 0 else 0
        
        alerts = []
        if total_allocated > 0:
            utilization_pct = (utilized / total_allocated) * 100
            if utilization_pct > 90:
                alerts.append(f"Critical utilization: {utilization_pct:.1f}%")
            elif utilization_pct > 80:
                alerts.append(f"High utilization: {utilization_pct:.1f}%")
        
        return {
            'pending_items': {
                'pending_proposals': pending_proposals,
                'pending_approvals': pending_expenditures,
                'pending_requests': pending_requests,
            },
            'recent_projects': cls._get_recent_projects(all_projects, limit=5),
            'budget_summary': {
                'total_allocated': float(total_allocated),
                'utilized': float(utilized),
                'remaining': float(remaining),
                'alerts': alerts,
            },
            'quick_stats': {
                'total_projects': all_projects.count(),
                'ongoing_projects': all_projects.filter(status='ONGOING').count(),
                'completed_projects': all_projects.filter(status='COMPLETED').count(),
                'pending_proposals': pending_proposals,
                'pending_expenditures': pending_expenditures,
                'pending_requests': pending_requests,
            }
        }
    
    # ========================================================================
    # DIRECTOR DASHBOARD
    # ========================================================================
    
    @classmethod
    def _get_director_dashboard(cls, username):
        """
        Director sees: Fund allocations pending, institute budget summary, research statistics
        Limited data visibility for administrative oversight
        """
        # Fund allocations pending Director approval
        pending_requests = Request.objects.filter(
            request_type='funds',
            status=RequestStatus.PENDING
        ).count()
        
        # Institute budget summary (high-level only)
        budgets = Budget.objects.all()
        total_allocated = budgets.aggregate(Sum('total_sanctioned'))['total_sanctioned__sum'] or 0
        utilized = budgets.aggregate(Sum('current_funds'))['current_funds__sum'] or 0
        remaining = total_allocated - utilized if total_allocated > 0 else 0
        
        # Research statistics
        all_projects = Project.objects.all()
        
        return {
            'pending_items': {
                'pending_requests': pending_requests,
            },
            'budget_summary': {
                'total_allocated': float(total_allocated),
                'utilized': float(utilized),
                'remaining': float(remaining),
                'alerts': [],
            },
            'quick_stats': {
                'total_projects': all_projects.count(),
                'ongoing_projects': all_projects.filter(status='ONGOING').count(),
                'completed_projects': all_projects.filter(status='COMPLETED').count(),
                'pending_requests': pending_requests,
            }
        }
    
    # ========================================================================
    # RSPC ADMIN DASHBOARD
    # ========================================================================
    
    @classmethod
    def _get_admin_dashboard(cls, username):
        """
        RSPC Admin sees: All pending items (proposals, expenditures, staff, requests),
        system statistics, user activity overview
        """
        all_projects = Project.objects.all()
        
        # All pending items
        pending_proposals = all_projects.filter(status='PROPOSED').count()
        pending_expenditures = Expenditure.objects.filter(status__startswith='pending').count()
        pending_staff = Staff.objects.filter(status__startswith='pending').count()
        pending_requests = Request.objects.filter(status=RequestStatus.PENDING).count()
        
        # Budget summary (all projects)
        budgets = Budget.objects.all()
        total_allocated = budgets.aggregate(Sum('total_sanctioned'))['total_sanctioned__sum'] or 0
        utilized = budgets.aggregate(Sum('current_funds'))['current_funds__sum'] or 0
        remaining = total_allocated - utilized if total_allocated > 0 else 0
        
        return {
            'pending_items': {
                'pending_proposals': pending_proposals,
                'pending_approvals': pending_expenditures,
                'pending_staff': pending_staff,
                'pending_requests': pending_requests,
            },
            'recent_projects': cls._get_recent_projects(all_projects, limit=5),
            'budget_summary': {
                'total_allocated': float(total_allocated),
                'utilized': float(utilized),
                'remaining': float(remaining),
                'alerts': [],
            },
            'quick_stats': {
                'total_projects': all_projects.count(),
                'ongoing_projects': all_projects.filter(status='ONGOING').count(),
                'completed_projects': all_projects.filter(status='COMPLETED').count(),
                'total_users': User.objects.filter(is_active=True).count(),
                'pending_proposals': pending_proposals,
                'pending_expenditures': pending_expenditures,
                'pending_staff': pending_staff,
                'pending_requests': pending_requests,
            }
        }
    
    # ========================================================================
    # COMMITTEE DASHBOARD
    # ========================================================================
    
    @classmethod
    def _get_committee_dashboard(cls, username):
        """
        Committee member sees: Assigned staff reviews, committee information, pending decisions
        """
        # Staff applications assigned to this committee member
        pending_decisions = Staff.objects.filter(
            committee__members__user__username=username,
            status__in=[StaffApprovalStatus.COMMITTEE_PENDING]
        ).count()
        
        return {
            'pending_items': {
                'pending_decisions': pending_decisions,
            },
            'quick_stats': {
                'pending_decisions': pending_decisions,
            }
        }
    
    # ========================================================================
    # GUEST DASHBOARD
    # ========================================================================
    
    @classmethod
    def _get_guest_dashboard(cls):
        """
        Guest/unauthenticated user sees: Public statistics only
        """
        all_projects = Project.objects.filter(status__in=['COMPLETED', 'ONGOING'])
        
        return {
            'quick_stats': {
                'total_projects': all_projects.count(),
                'ongoing_projects': all_projects.filter(status='ONGOING').count(),
                'completed_projects': all_projects.filter(status='COMPLETED').count(),
            }
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @classmethod
    def _get_recent_projects(cls, projects_qs, limit=5):
        """Get recent projects with summary info"""
        recent = projects_qs.order_by('-created_at')[:limit]
        return [
            {
                'id': p.pid,
                'name': p.name,
                'status': p.status,
                'budget': float(p.total_budget) if p.total_budget else 0,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in recent
        ]
    
    @classmethod
    def _get_unread_notifications(cls, username):
        """Count unread notifications for user"""
        try:
            return Notification.objects.filter(
                user__username=username,
                is_read=False
            ).count()
        except:
            return 0
    
    @classmethod
    def _get_recent_notifications(cls, username, limit=5):
        """Get recent notifications"""
        try:
            notifications = Notification.objects.filter(
                user__username=username
            ).order_by('-created_at')[:limit]
            
            return [
                {
                    'id': n.id,
                    'message': n.message,
                    'event_type': n.event_type,
                    'is_read': n.is_read,
                    'created_at': n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifications
            ]
        except:
            return []

"""
RSPC Module - Budget Management Services (UC-011)
Handles budget allocation, reallocation, utilization tracking, and enforcement
of BR-RSPC-08 (Max 20% reallocation) and BR-RSPC-11 (Admin-only utilization updates)
"""

from typing import Tuple, Dict
from decimal import Decimal
import datetime as dt
from django.contrib.auth.models import User

from applications.globals.models import ExtraInfo

from .models import (
    Project, Budget, BudgetReallocation, BudgetModificationHistory,
    ProjectAccess, Notification
)


def check_project_access_by_role(project_id: int, username: str) -> bool:
    """
    Check if user has access to view/modify project based on role
    
    Role-based access:
    - PI/Co-PI: Own projects only
    - HOD: Department projects
    - Dean RSPC: All projects
    - RSPC Admin: All projects (unrestricted)
    """
    try:
        from .role_filters import get_user_roles
        
        project = Project.objects.get(pid=project_id)
        user_roles = get_user_roles(username)
        
        # RSPC Admin has full access
        if user_roles.get('rspc_admin'):
            return True
        
        # Dean RSPC has full access
        if user_roles.get('dean_rspc'):
            return True
        
        # PI/Co-PI: check own projects
        if project.pi_id == username or ProjectAccess.objects.filter(
            pid=project, member_id=username
        ).exists():
            return True
        
        # HOD: check department projects
        if user_roles.get('hod'):
            try:
                user = User.objects.get(username=username)
                extra_info = ExtraInfo.objects.get(user=user)
                if project.dept == str(extra_info.department):
                    return True
            except (User.DoesNotExist, ExtraInfo.DoesNotExist):
                pass
        
        return False
    except Project.DoesNotExist:
        return False


def can_modify_budget(project_id: int, username: str) -> bool:
    """
    Check if user can modify budget for project
    
    Only PI/Co-PI and RSPC Admin can modify budget
    """
    try:
        from .role_filters import get_user_roles
        
        project = Project.objects.get(pid=project_id)
        user_roles = get_user_roles(username)
        
        # RSPC Admin can modify any budget
        if user_roles.get('rspc_admin'):
            return True
        
        # Only PI/Co-PI can request reallocation
        if project.pi_id == username or ProjectAccess.objects.filter(
            pid=project, member_id=username
        ).exists():
            return True
        
        return False
    except Project.DoesNotExist:
        return False


def is_user_rspc_admin(username: str) -> bool:
    """Check if user is RSPC Admin (for BR-RSPC-11 enforcement)"""
    from .role_filters import get_user_roles
    user_roles = get_user_roles(username)
    return user_roles.get('rspc_admin', False)


def get_category_field(category: str) -> str:
    """Convert category to model field name"""
    category_map = {
        'MANPOWER': 'manpower',
        'TRAVEL': 'travel',
        'CONSUMABLES': 'consumables',
        'EQUIPMENT': 'equipment',
        'CONTINGENCY': 'contingency',
        'OVERHEAD': 'overhead',
    }
    return category_map.get(category, category.lower())


def send_budget_notification(project_id: int, subject: str, message: str, recipient: str):
    """Send notification about budget changes"""
    try:
        Notification.objects.create(
            recipient=recipient,
            subject=subject,
            message=message,
            entity_type='budget',
            entity_id=str(project_id),
            is_read=False
        )
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")


def implement_budget_reallocation(reallocation, implemented_by: str):
    """
    Implement a budget reallocation
    
    Updates budget JSONFields to move funds from one category to another
    """
    budget = reallocation.budget
    from_category = get_category_field(reallocation.from_category)
    to_category = get_category_field(reallocation.to_category)
    amount = reallocation.amount
    year = reallocation.financial_year
    
    # Update from_category
    from_cat_data = getattr(budget, from_category, {}) or {}
    if year in from_cat_data:
        from_cat_data[year] = float(from_cat_data[year]) - float(amount)
    setattr(budget, from_category, from_cat_data)
    
    # Update to_category
    to_cat_data = getattr(budget, to_category, {}) or {}
    if year not in to_cat_data:
        to_cat_data[year] = 0
    to_cat_data[year] = float(to_cat_data[year]) + float(amount)
    setattr(budget, to_category, to_cat_data)
    
    budget.modified_by = implemented_by
    budget.save()
    
    # Create history record
    BudgetModificationHistory.objects.create(
        budget=budget,
        modification_type='REALLOCATION',
        category=reallocation.from_category,
        old_value=None,
        new_value=None,
        change_amount=amount,
        reason=f"Reallocation from {reallocation.from_category} to {reallocation.to_category}",
        modified_by=implemented_by,
        related_reallocation=reallocation
    )
    
    # Update reallocation status
    reallocation.approval_status = 'IMPLEMENTED'
    reallocation.approved_by = implemented_by
    reallocation.approved_at = dt.datetime.now(dt.timezone.utc)
    reallocation.implemented_at = dt.datetime.now(dt.timezone.utc)
    reallocation.save()


def validate_reallocation_limit(budget, category: str, amount, year: str) -> Tuple[bool, str]:
    """
    Validate BR-RSPC-08: Max 20% reallocation per category per year
    
    Returns (is_valid, message)
    """
    category_field = get_category_field(category)
    category_data = getattr(budget, category_field, {}) or {}
    
    year_budget = Decimal(str(category_data.get(year, 0)))
    
    if year_budget <= 0:
        return False, f"No budget allocated for {category} in {year}"
    
    # Check if this reallocation would exceed 20% of category budget
    if amount > (year_budget * Decimal('0.2')):
        limit_val = year_budget * Decimal('0.2')
        return False, f"Reallocation of amount {amount} exceeds 20% limit of {limit_val} for {category} in {year}"
    
    return True, "Reallocation is within 20% limit"


def get_budget_summary(project_id: int) -> dict:
    """
    Get comprehensive budget summary for a project
    
    Used internally by get_budget view
    """
    try:
        project = Project.objects.get(pid=project_id)
        budget, _ = Budget.objects.get_or_create(
            project=project,
            defaults={
                'total_sanctioned': project.sanctioned_amount or project.total_budget,
                'current_funds': Decimal('0')
            }
        )
        
        categories = ['manpower', 'travel', 'consumables', 'equipment', 'contingency', 'overhead']
        categories_detail = {}
        
        for cat in categories:
            cat_budget = getattr(budget, cat, {}) or {}
            if isinstance(cat_budget, dict):
                cat_total = sum(Decimal(str(v)) for v in cat_budget.values() if isinstance(v, (int, float, Decimal)))
            else:
                cat_total = Decimal('0')
            
            cat_util = budget.get_category_utilization(cat)
            categories_detail[cat] = {
                'allocated': float(cat_total),
                'utilized': float(cat_util),
                'available': float(cat_total - cat_util),
                'utilization_percentage': round((float(cat_util) / float(cat_total) * 100) if cat_total > 0 else 0, 2)
            }
        
        return {
            'project_id': project_id,
            'project_name': project.name,
            'total_sanctioned': float(budget.total_sanctioned),
            'current_funds': float(budget.current_funds),
            'total_budget': float(budget.get_total_budget()),
            'available_balance': float(budget.total_sanctioned - budget.current_funds),
            'utilization_percentage': round(budget.get_utilization_percentage(), 2),
            'categories': categories_detail
        }
    except Project.DoesNotExist:
        return {'error': 'Project not found'}

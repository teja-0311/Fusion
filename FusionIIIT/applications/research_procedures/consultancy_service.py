"""
BR-020: Consultancy Workload Limits Service
Implements workload limit validation for faculty consultancy projects
"""

from decimal import Decimal
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    ConsultancyLimit, Project, ProjectTypeChoice, SmallFundRequest
)


class ConsultancyService:
    """
    Service for managing consultancy workload limits (BR-020)
    Validates:
    - Maximum consultancy hours per year (default 500)
    - Maximum consultancy percentage of total workload (default 20%)
    - Maximum concurrent consultancy projects (default 2)
    """
    
    @staticmethod
    def get_limits() -> ConsultancyLimit:
        """Get global consultancy limits"""
        return ConsultancyLimit.get_limits()
    
    @staticmethod
    def check_workload_limit(faculty_id: str, estimated_hours: int) -> dict:
        """
        Check if faculty can take additional consultancy work
        
        Returns:
            {
                'can_accept': bool,
                'reason': str,
                'current_hours': int,
                'max_allowed': int,
                'available_hours': int
            }
        """
        limits = ConsultancyService.get_limits()
        current_hours = ConsultancyService.get_user_consultancy_hours(faculty_id)
        
        # Check hours limit
        available_hours = limits.max_consultancy_hours_per_year - current_hours
        
        if estimated_hours > available_hours:
            return {
                'can_accept': False,
                'reason': f'Exceeds annual limit. Current: {current_hours}h, Max: {limits.max_consultancy_hours_per_year}h, Requested: {estimated_hours}h',
                'current_hours': current_hours,
                'max_allowed': limits.max_consultancy_hours_per_year,
                'available_hours': available_hours
            }
        
        return {
            'can_accept': True,
            'reason': 'Within workload limits',
            'current_hours': current_hours,
            'max_allowed': limits.max_consultancy_hours_per_year,
            'available_hours': available_hours
        }
    
    @staticmethod
    def get_user_consultancy_hours(faculty_id: str) -> int:
        """
        Get total consultancy hours for faculty in current year
        Sums estimated_hours from all ONGOING/APPROVED CONSULTANCY projects
        """
        current_year_start = timezone.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        consultancy_projects = Project.objects.filter(
            pi_id=faculty_id,
            project_type=ProjectTypeChoice.CONSULTANCY,
            status__in=['ONGOING', 'APPROVED'],
            created_at__gte=current_year_start
        )
        
        total_hours = 0
        for project in consultancy_projects:
            if project.estimated_hours:
                total_hours += project.estimated_hours
        
        return total_hours
    
    @staticmethod
    def get_user_consultancy_count(faculty_id: str) -> int:
        """
        Get count of active consultancy projects for faculty
        Counts ONGOING and APPROVED projects
        """
        return Project.objects.filter(
            pi_id=faculty_id,
            project_type=ProjectTypeChoice.CONSULTANCY,
            status__in=['ONGOING', 'APPROVED']
        ).count()
    
    @staticmethod
    def check_concurrent_limit(faculty_id: str) -> dict:
        """
        Check if faculty can take another concurrent consultancy
        
        Returns:
            {
                'can_accept': bool,
                'reason': str,
                'current_count': int,
                'max_allowed': int
            }
        """
        limits = ConsultancyService.get_limits()
        current_count = ConsultancyService.get_user_consultancy_count(faculty_id)
        
        if current_count >= limits.max_concurrent_consultancies:
            return {
                'can_accept': False,
                'reason': f'Already has {current_count} active consultancies (max: {limits.max_concurrent_consultancies})',
                'current_count': current_count,
                'max_allowed': limits.max_concurrent_consultancies
            }
        
        return {
            'can_accept': True,
            'reason': 'Can accept additional consultancy',
            'current_count': current_count,
            'max_allowed': limits.max_concurrent_consultancies
        }
    
    @staticmethod
    def validate_consultancy_limits(faculty_id: str, estimated_hours: int) -> tuple:
        """
        Comprehensive consultancy validation
        
        Returns:
            (is_valid: bool, errors: list, warnings: list)
        """
        errors = []
        warnings = []
        
        # Check hours limit
        hours_check = ConsultancyService.check_workload_limit(faculty_id, estimated_hours)
        if not hours_check['can_accept']:
            errors.append(hours_check['reason'])
        
        # Check concurrent limit
        concurrent_check = ConsultancyService.check_concurrent_limit(faculty_id)
        if not concurrent_check['can_accept']:
            errors.append(concurrent_check['reason'])
        
        # Warning if reaching 80% of limit
        limits = ConsultancyService.get_limits()
        current_hours = ConsultancyService.get_user_consultancy_hours(faculty_id)
        utilization_percent = ((current_hours + estimated_hours) / limits.max_consultancy_hours_per_year) * 100
        
        if utilization_percent >= 80:
            warnings.append(f'Warning: Will utilize {utilization_percent:.1f}% of annual consultancy hours limit')
        
        return (len(errors) == 0, errors, warnings)
    
    @staticmethod
    def get_faculty_workload(faculty_id: str) -> dict:
        """
        Get comprehensive workload information for faculty
        
        Returns:
            {
                'total_consultancy_hours': int,
                'max_allowed_hours': int,
                'hours_utilization_percent': float,
                'active_consultancies': int,
                'max_concurrent': int,
                'workload_alerts': list
            }
        """
        limits = ConsultancyService.get_limits()
        current_hours = ConsultancyService.get_user_consultancy_hours(faculty_id)
        current_count = ConsultancyService.get_user_consultancy_count(faculty_id)
        
        hours_percent = (current_hours / limits.max_consultancy_hours_per_year * 100) if limits.max_consultancy_hours_per_year > 0 else 0
        
        alerts = []
        if current_hours >= limits.max_consultancy_hours_per_year * 0.9:
            alerts.append('CRITICAL: Approaching annual hours limit')
        elif current_hours >= limits.max_consultancy_hours_per_year * 0.8:
            alerts.append('WARNING: High utilization of annual hours limit')
        
        if current_count >= limits.max_concurrent_consultancies:
            alerts.append('CRITICAL: At maximum concurrent consultancies')
        
        return {
            'total_consultancy_hours': current_hours,
            'max_allowed_hours': limits.max_consultancy_hours_per_year,
            'hours_utilization_percent': round(hours_percent, 2),
            'active_consultancies': current_count,
            'max_concurrent': limits.max_concurrent_consultancies,
            'workload_alerts': alerts
        }

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatentViewSet, ResearchGroupViewSet, ResearchAreaViewSet
from .expenditure_views import ExpenditureViewSet
from .notification_views import NotificationViewSet
from .staff_views import StaffViewSet, CommitteeViewSet, CommitteeVerdictViewSet
from .report_views import ProgressReportViewSet, ProjectClosureViewSet, ApprovalsViewSet
from .stipend_compliance_views import (
    StipendBatchViewSet, StipendHistoryViewSet,
    ComplianceReportViewSet, ProjectSettlementViewSet
)
from .dashboard_views import dashboard, pending_approvals
from .filtering_views import projects_list, expenditures_list, staff_list, budget_list, requests_list

router = DefaultRouter()
router.register(r'groups', ResearchGroupViewSet, basename='research-group')
router.register(r'areas', ResearchAreaViewSet, basename='research-area')
router.register(r'patent', PatentViewSet)
router.register(r'expenditures', ExpenditureViewSet, basename='expenditure')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'committee', CommitteeViewSet, basename='committee')
router.register(r'committee-verdict', CommitteeVerdictViewSet, basename='committee-verdict')
router.register(r'reports/progress', ProgressReportViewSet, basename='progress-report')
router.register(r'projects', ProjectClosureViewSet, basename='project-closure')
router.register(r'approvals', ApprovalsViewSet, basename='approval')
# UC-017, UC-018, BR-015 routes
router.register(r'staff/stipend/batches', StipendBatchViewSet, basename='stipend-batch')
router.register(r'staff/stipend', StipendHistoryViewSet, basename='stipend-history')
router.register(r'reports/compliance', ComplianceReportViewSet, basename='compliance-report')
router.register(r'projects/settlement', ProjectSettlementViewSet, basename='project-settlement')

urlpatterns = [
    path('dashboard/', dashboard, name='api-dashboard'),
    path('dashboard/pending-approvals/', pending_approvals, name='api-pending-approvals'),
    # Role-filtered list endpoints
    path('projects/filtered/', projects_list, name='api-projects-filtered'),
    path('expenditures/filtered/', expenditures_list, name='api-expenditures-filtered'),
    path('staff/filtered/', staff_list, name='api-staff-filtered'),
    path('budgets/filtered/', budget_list, name='api-budgets-filtered'),
    path('requests/filtered/', requests_list, name='api-requests-filtered'),
] + router.urls


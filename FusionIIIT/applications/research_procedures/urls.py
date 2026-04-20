"""
RSPC Module - URL Configuration
API Route Mapping - Complete 38 endpoints
"""

from django.urls import path
from . import views

app_name = 'rspc'

urlpatterns = [
    # ========================================================================
    # AUTHENTICATION ENDPOINTS (2)
    # ========================================================================
    path('api/rspc-login/', views.rspc_login_api, name='rspc_login_api'),
    path('api/rspc-auto-login/', views.rspc_auto_login, name='rspc_auto_login'),
    
    # ========================================================================
    # PROJECT PROPOSAL ENDPOINTS (4)
    # ========================================================================
    path('proposals/submit/', views.submit_proposal, name='submit_proposal'),
    path('consultancy/submit/', views.submit_consultancy, name='submit_consultancy'),
    path('proposals/draft/', views.save_draft, name='save_draft'),
    path('proposals/<int:project_id>/resubmit/', views.resubmit_proposal, name='resubmit_proposal'),
    
    # ========================================================================
    # PROJECT MANAGEMENT ENDPOINTS (6)
    # ========================================================================
    path('projects/', views.get_projects, name='get_projects'),
    path('projects/<int:project_id>/', views.get_project_details, name='get_project_details'),
    path('projects/<int:project_id>/register/', views.register_project, name='register_project'),
    path('projects/<int:project_id>/commence/', views.commence_project, name='commence_project'),
    path('projects/<int:project_id>/close/', views.close_project, name='close_project'),
    path('projects/<int:project_id>/lifecycle/', views.get_project_lifecycle, name='get_project_lifecycle'),
    
    # ========================================================================
    # STAFF MANAGEMENT ENDPOINTS (10)
    # ========================================================================
    path('staff/request/', views.request_staff, name='request_staff'),
    path('staff/ad-committee/', views.add_ad_committee, name='add_ad_committee'),
    path('staff/selection-report/', views.staff_selection_report, name='staff_selection_report'),
    path('staff/<int:staff_id>/recommend/', views.committee_action, name='committee_action'),
    path('staff/<int:staff_id>/decision/', views.staff_decision, name='staff_decision'),
    path('staff/<int:staff_id>/withdraw/', views.withdraw_staff_request, name='withdraw_staff_request'),
    path('staff/<int:staff_id>/documents/', views.staff_document_upload, name='staff_document_upload'),
    path('staff/<int:staff_id>/committee-verdict/', views.submit_committee_verdict, name='submit_committee_verdict'),
    path('staff/committee/create/', views.create_staff_committee, name='create_staff_committee'),
    path('staff/', views.get_staff, name='get_staff'),
    path('staff/positions/', views.get_staff_positions, name='get_staff_positions'),
    
    # ========================================================================
    # BUDGET MANAGEMENT ENDPOINTS (5) - UC-011 Complete Implementation
    # ========================================================================
    path('api/budget/<int:project_id>/', views.get_budget, name='get_budget'),
    path('api/budget/<int:project_id>/reallocate/', views.reallocate_budget, name='reallocate_budget'),
    path('api/budget/<int:project_id>/tracking/', views.get_budget_tracking, name='get_budget_tracking'),
    path('api/budget/<int:project_id>/update-utilized/', views.update_budget_utilized, name='update_budget_utilized'),
    path('api/budget/<int:project_id>/history/', views.get_budget_history, name='get_budget_history'),
    
    # ========================================================================
    # EXPENDITURE MANAGEMENT ENDPOINTS (10)
    # ========================================================================
    path('expenditures/', views.create_expenditure, name='create_expenditure'),
    path('expenditures/list/', views.list_expenditures, name='list_expenditures'),
    path('expenditures/create-with-workflow/', views.create_expenditure_workflow, name='create_expenditure_workflow'),
    path('expenditures/<int:expenditure_id>/', views.get_expenditure_details, name='get_expenditure_details'),
    path('expenditures/<int:expenditure_id>/track/', views.track_expenditure_status, name='track_expenditure_status'),
    path('expenditures/<int:expenditure_id>/approve/', views.approve_expenditure, name='approve_expenditure'),
    path('expenditures/<int:expenditure_id>/approve-with-workflow/', views.approve_expenditure_workflow, name='approve_expenditure_workflow'),
    path('expenditures/<int:expenditure_id>/reject/', views.reject_expenditure, name='reject_expenditure'),
    path('expenditures/<int:expenditure_id>/reject-with-workflow/', views.reject_expenditure_workflow, name='reject_expenditure_workflow'),
    path('expenditures/<int:expenditure_id>/history/', views.expenditure_history, name='expenditure_history'),
    
    # ========================================================================
    # FUND REQUEST ENDPOINTS (3)
    # ========================================================================
    path('funds/request/', views.request_fund, name='request_fund'),
    path('funds/<int:fund_id>/dean-action/', views.dean_fund_action, name='dean_fund_action'),
    path('funds/<int:fund_id>/director-approve/', views.director_approve_fund, name='director_approve_fund'),
    
    # ========================================================================
    # PROGRESS REPORT ENDPOINTS (1)
    # ========================================================================
    path('reports/submit/', views.submit_progress_report, name='submit_progress_report'),
    
    # ========================================================================
    # REPORT GENERATION ENDPOINTS (3)
    # ========================================================================
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('reports/schedule/', views.schedule_report, name='schedule_report'),
    path('reports/scheduled/', views.list_scheduled_reports, name='list_scheduled_reports'),
    
    # ========================================================================
    # APPROVAL WORKFLOW ENDPOINTS (2)
    # ========================================================================
    path('proposals/<int:project_id>/verify/', views.verify_proposal, name='verify_proposal'),
    path('proposals/<int:project_id>/dean-action/', views.dean_proposal_action, name='dean_proposal_action'),
    
    # ========================================================================
    # COMMITTEE MANAGEMENT ENDPOINTS (1)
    # ========================================================================
    path('committees/<int:committee_id>/extend-deadline/', 
         views.extend_committee_deadline, 
         name='extend_committee_deadline'),
    
    # ========================================================================
    # NOTIFICATION ENDPOINTS (2)
    # ========================================================================
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/mark-read/', 
         views.mark_notification_read, 
         name='mark_notification_read'),
    
    # ========================================================================
    # VALIDATION ENDPOINTS (Phase 1 - BR validations)
    # ========================================================================
    path('utils/validate-pi/<str:username>/', views.validate_pi_eligibility, name='validate_pi_eligibility'),
    path('utils/validate-duration/', views.validate_duration, name='validate_duration'),
    path('utils/validate-committee/', views.validate_committee_members, name='validate_committee_members'),
    path('utils/validate-budget-reallocation/', views.validate_budget_reallocation, name='validate_budget_reallocation'),
    
    # ========================================================================
    # UTILITY ENDPOINTS (3)
    # ========================================================================
    path('utils/co-pis/', views.get_copis, name='get_copis'),
    path('utils/faculty-ids/', views.get_faculty_ids, name='get_faculty_ids'),
    path('utils/project-ids/', views.get_project_ids, name='get_project_ids'),
    
    # ========================================================================
    # DASHBOARD ENDPOINTS (2)
    # ========================================================================
    path('dashboard/', views.get_dashboard, name='dashboard'),
    path('dashboard/pending-approvals/', views.get_pending_approvals, name='get_pending_approvals'),
    
    # ========================================================================
    # UC-004: PROJECT UPDATE ENDPOINTS (3)
    # ========================================================================
    path('projects/<int:project_id>/', views.update_project, name='update_project'),
    path('projects/<int:project_id>/versions/', views.list_project_versions, name='list_project_versions'),
    path('projects/<int:project_id>/versions/<int:version_id>/', views.get_project_version, name='get_project_version'),
    
    # ========================================================================
    # UC-005: PROJECT CANCELLATION ENDPOINTS (3)
    # ========================================================================
    path('projects/<int:project_id>/cancel/', views.cancel_project, name='cancel_project'),
    path('projects/<int:project_id>/cancellation-details/', views.get_cancellation_details, name='get_cancellation_details'),
    path('projects/<int:project_id>/cancel-request/', views.request_project_cancellation, name='request_project_cancellation'),
    
    # ========================================================================
    # UC-012: PROPOSAL VETTING ENDPOINTS (4)
    # ========================================================================
    path('proposals/<int:project_id>/vet/', views.vet_proposal, name='vet_proposal'),
    path('proposals/<int:project_id>/vetting/', views.get_vetting_details, name='get_vetting_details'),
    path('proposals/pending-vetting/', views.list_pending_vetting, name='list_pending_vetting'),
    path('proposals/<int:project_id>/vetting/revert/', views.revert_vetting, name='revert_vetting'),
    
    # ========================================================================
    # UC-013: DEPARTMENT PROJECTS ENDPOINTS (2)
    # ========================================================================
    path('projects/department/', views.get_department_projects, name='get_department_projects'),
    path('projects/department/summary/', views.get_department_summary, name='get_department_summary'),
    
    # ========================================================================
    # UC-021: SMALL FUND REQUEST ENDPOINTS (5)
    # ========================================================================
    path('funds/small/request/', views.create_small_fund_request, name='create_small_fund_request'),
    path('funds/small/request/<int:request_id>/', views.get_small_fund_request_details, name='get_small_fund_request_details'),
    path('funds/small/request/<int:request_id>/update/', views.update_small_fund_request, name='update_small_fund_request'),
    path('funds/small/request/<int:request_id>/submit/', views.submit_small_fund_request, name='submit_small_fund_request'),
    path('funds/small/requests/', views.list_small_fund_requests, name='list_small_fund_requests'),
    
    # ========================================================================
    # UC-022: SMALL FUND APPROVAL ENDPOINTS (3)
    # ========================================================================
    path('funds/small/request/<int:request_id>/approve/', views.approve_small_fund_request, name='approve_small_fund_request'),
    path('funds/small/request/<int:request_id>/reject/', views.reject_small_fund_request, name='reject_small_fund_request'),
    path('funds/small/pending-approvals/', views.get_pending_small_fund_approvals, name='get_pending_small_fund_approvals'),
    
    # ========================================================================
    # UC-023: FUND DISBURSEMENT ENDPOINTS (4)
    # ========================================================================
    path('funds/small/request/<int:request_id>/disburse/', views.disburse_small_fund, name='disburse_small_fund'),
    path('funds/small/request/<int:request_id>/disbursement/', views.get_fund_disbursement_status, name='get_fund_disbursement_status'),
    path('funds/small/disbursements/', views.list_all_disbursements, name='list_all_disbursements'),
    path('funds/small/request/<int:request_id>/disbursement/mark-failed/', views.mark_disbursement_failed, name='mark_disbursement_failed'),
    
    # ========================================================================
    # BR-020: CONSULTANCY WORKLOAD ENDPOINTS (5)
    # ========================================================================
    path('consultancy/validate-limits/', views.validate_consultancy_limits, name='validate_consultancy_limits'),
    path('consultancy/faculty/<str:user_id>/workload/', views.get_faculty_consultancy_workload, name='get_faculty_consultancy_workload'),
    path('consultancy/limits/', views.manage_consultancy_limits, name='manage_consultancy_limits'),
    path('consultancy/alerts/', views.get_consultancy_workload_alerts, name='get_consultancy_workload_alerts'),
    path('projects/type-consultancy/create/', views.create_consultancy_project, name='create_consultancy_project'),
]


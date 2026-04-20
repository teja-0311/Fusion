"""
RSPC Module - Unit and Integration Tests
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
import json

from applications.globals.models import ExtraInfo, Faculty, DepartmentInfo, Designation, HoldsDesignation
from ..models import Project, Staff, Budget, FinancialOutlay, StaffAllocation
from ..services import validate_pi_eligibility, validate_rspc_admin


class RSPCTestCase(TestCase):
    """Base test case with setup"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        
        self.faculty_user = User.objects.create_user(
            username='faculty1',
            password='faculty123',
            first_name='Faculty',
            last_name='One'
        )
        
        self.student_user = User.objects.create_user(
            username='student1',
            password='student123',
            first_name='Student',
            last_name='One'
        )
        
        # Create department
        self.dept = DepartmentInfo.objects.create(
            name='Computer Science',
            code='CSE'
        )
        
        # Create ExtraInfo
        self.admin_extrainfo = ExtraInfo.objects.create(
            user=self.admin_user,
            id=f"admin_{self.admin_user.id}",
            user_type='staff',
            department=self.dept
        )
        
        self.faculty_extrainfo = ExtraInfo.objects.create(
            user=self.faculty_user,
            id=f"faculty_{self.faculty_user.id}",
            user_type='faculty',
            department=self.dept
        )
        
        # Create Faculty
        self.faculty = Faculty.objects.create(
            id=self.faculty_extrainfo
        )
        
        # Create designations
        self.prof_designation = Designation.objects.create(name='Professor')
        self.asstprof_designation = Designation.objects.create(name='Assistant Professor')
        self.rspc_admin_designation = Designation.objects.create(name='rspc_admin')
        
        # Assign designations
        HoldsDesignation.objects.create(
            user=self.faculty_user,
            designation=self.prof_designation
        )
        
        HoldsDesignation.objects.create(
            user=self.admin_user,
            designation=self.rspc_admin_designation
        )
        
        # Create test client
        self.client = Client()
        
        # Create a test project
        self.project = Project.objects.create(
            name='Test Project',
            pi_id='faculty1',
            pi_name='Faculty One',
            type='Research',
            dept='CSE',
            category='Sponsored',
            sponsored_agency='DST',
            scheme='Core Research',
            description='Test project description',
            duration=12,
            total_budget=1000000,
            status='PROPOSED'
        )


class ServiceLayerTests(RSPCTestCase):
    """Test service layer functions"""
    
    def test_validate_pi_eligibility(self):
        """Test PI eligibility validation (BR-RSPC-03)"""
        # Faculty with Professor designation should be eligible
        self.assertTrue(validate_pi_eligibility('faculty1'))
        
        # Student should not be eligible
        self.assertFalse(validate_pi_eligibility('student1'))
        
        # Non-existent user should not be eligible
        self.assertFalse(validate_pi_eligibility('nonexistent'))
    
    def test_validate_rspc_admin(self):
        """Test RSPC admin validation (BR-RSPC-04)"""
        # Admin with rspc_admin designation should be valid
        self.assertTrue(validate_rspc_admin('admin'))
        
        # Faculty without rspc_admin should not be valid
        self.assertFalse(validate_rspc_admin('faculty1'))
    
    def test_unique_project_name(self):
        """Test unique project name constraint (BR-RSPC-05)"""
        # Creating project with same name should fail
        from ..services import submit_research_proposal
        
        data = {
            'name': 'Test Project',  # Already exists
            'pi_id': 'faculty1',
            'pi_name': 'Faculty One',
            'type': 'Research',
            'dept': 'CSE',
            'total_budget': 500000,
        }
        
        user_info = {'username': 'admin'}
        success, message, project = submit_research_proposal(data, user_info)
        
        self.assertFalse(success)
        self.assertIn('unique', message.lower())
    
    def test_pi_copi_distinction(self):
        """Test PI cannot be Co-PI (BR-RSPC-06)"""
        from ..services import submit_research_proposal
        
        data = {
            'name': 'New Unique Project',
            'pi_id': 'faculty1',
            'pi_name': 'Faculty One',
            'type': 'Research',
            'dept': 'CSE',
            'total_budget': 500000,
            'co_pis': ['faculty1']  # PI in Co-PI list
        }
        
        user_info = {'username': 'admin'}
        success, message, project = submit_research_proposal(data, user_info)
        
        self.assertFalse(success)
        self.assertIn('cannot also be', message.lower())


class ProjectAPITests(RSPCTestCase):
    """Test project API endpoints"""
    
    def test_submit_proposal_unauthorized(self):
        """Test proposal submission without authentication"""
        url = reverse('rspc:submit_proposal')
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_submit_proposal_as_admin(self):
        """Test proposal submission as RSPC admin"""
        self.client.login(username='admin', password='admin123')
        
        url = reverse('rspc:submit_proposal')
        data = {
            'name': 'New Research Project',
            'pi_id': 'faculty1',
            'pi_name': 'Faculty One',
            'type': 'Research',
            'dept': 'CSE',
            'category': 'Sponsored',
            'sponsored_agency': 'SERB',
            'scheme': 'Core Research',
            'description': 'This is a test research project',
            'duration': 24,
            'total_budget': 1500000,
            'co_pis': []
        }
        
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json()['success'])
        
        # Verify project was created
        self.assertTrue(Project.objects.filter(name='New Research Project').exists())
    
    def test_get_projects_as_faculty(self):
        """Test getting projects as faculty (should see only own)"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:get_projects')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        # Should see at least the test project
        self.assertGreaterEqual(data['count'], 1)
    
    def test_get_project_details(self):
        """Test getting project details"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:get_project_details', args=[self.project.pid])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['project']['name'], 'Test Project')


class StaffAPITests(RSPCTestCase):
    """Test staff management API endpoints"""
    
    def test_request_staff(self):
        """Test staff request creation"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:request_staff')
        data = {
            'project_id': self.project.pid,
            'person': 'John Doe',
            'type': 'JRF',
            'salary': 31000,
            'duration': 12,
        }
        
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json()['success'])
        
        # Verify staff was created
        self.assertTrue(Staff.objects.filter(person='John Doe').exists())
    
    def test_get_staff(self):
        """Test getting staff list"""
        # First create a staff member
        Staff.objects.create(
            pid=self.project,
            person='Jane Smith',
            uname='faculty1',
            type='SRF',
            salary=35000,
            duration=12,
            approval_status='DRAFT'
        )
        
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:get_staff')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)


class BudgetAPITests(RSPCTestCase):
    """Test budget management API endpoints"""
    
    def setUp(self):
        super().setUp()
        # Create budget for project
        self.budget = Budget.objects.create(
            pid=self.project,
            manpower={'year1': 500000},
            travel={'year1': 100000},
            contingency={'year1': 50000},
            consumables={'year1': 150000},
            equipments={'year1': 200000},
            overhead=10,
            total_budget=1000000,
            current_funds=0
        )
    
    def test_get_budget(self):
        """Test getting project budget"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:get_budget', args=[self.project.pid])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['budget']['total_budget'], 1000000.0)


class ExpenditureAPITests(RSPCTestCase):
    """Test expenditure management API endpoints"""
    
    def test_create_expenditure(self):
        """Test creating expenditure request"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:create_expenditure')
        data = {
            'project_id': self.project.pid,
            'category': 'Equipment',
            'amount': 50000,
            'purpose': 'Purchase laptop',
            'supporting_documents': []
        }
        
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json()['success'])


class UtilityAPITests(RSPCTestCase):
    """Test utility API endpoints"""
    
    def test_get_faculty_ids(self):
        """Test getting faculty IDs"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:get_faculty_ids')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)
    
    def test_get_project_ids(self):
        """Test getting project IDs"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:get_project_ids')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)


class DashboardAPITests(RSPCTestCase):
    """Test dashboard API endpoint"""
    
    def test_get_dashboard(self):
        """Test getting dashboard data"""
        self.client.login(username='faculty1', password='faculty123')
        
        url = reverse('rspc:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('dashboard', data)
        self.assertIn('projects', data['dashboard'])
        self.assertIn('notifications', data['dashboard'])
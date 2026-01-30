from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Interview, InterviewStatusMaster

User = get_user_model()

class InterviewCreateTest(TestCase):
    def setUp(self):
        # Create users
        self.manager = User.objects.create_user(username='manager', password='password')
        self.employee = User.objects.create_user(username='employee', password='password')
        self.client.login(username='manager', password='password')
        
    def test_create_without_schedule_fails(self):
        # Attempt to create interview without scheduled_at
        response = self.client.post(reverse('interview_create'), {
            'employee': self.employee.id,
            'theme': 'Test Theme',
            'location': 'Meeting Room',
            'scheduled_at': '' # Empty date
        })
        
        # Should not redirect to detail (success) but stay on create page (or redirect back to create)
        # However, current implementation might incorrectly succeed or error out. 
        # Ideally, it should fail validation.
        
        # Check if interview was created
        self.assertEqual(Interview.objects.count(), 0)

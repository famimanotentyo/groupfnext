from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Manual, ManualStatusMaster, ManualVisibilityMaster

User = get_user_model()

class ManualListTest(TestCase):
    def setUp(self):
        # Create Status Masters
        self.approved_status = ManualStatusMaster.objects.create(code='approved', name='Approved')
        self.pending_status = ManualStatusMaster.objects.create(code='pending', name='Pending')
        self.rejected_status = ManualStatusMaster.objects.create(code='rejected', name='Rejected')

        # Create Visibility Master (needed for Manual creation if required, though null=True in model)
        self.public_visibility = ManualVisibilityMaster.objects.create(code='public', name='Public')

        # Create User
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_rejected_manual_not_in_list(self):
        # Create a rejected manual owned by the user
        rejected_manual = Manual.objects.create(
            title='Rejected Manual',
            description='This is a rejected manual',
            status=self.rejected_status,
            visibility=self.public_visibility,
            created_by=self.user
        )

        # Create a pending manual owned by the user (should be visible)
        pending_manual = Manual.objects.create(
            title='Pending Manual',
            description='This is a pending manual',
            status=self.pending_status,
            visibility=self.public_visibility,
            created_by=self.user
        )

        # Create an approved manual (should be visible)
        approved_manual = Manual.objects.create(
            title='Approved Manual',
            description='This is an approved manual',
            status=self.approved_status,
            visibility=self.public_visibility,
            created_by=self.user
        )

        response = self.client.get(reverse('manual_list'))
        
        self.assertEqual(response.status_code, 200)
        manuals = response.context['manuals']
        
        # Check that rejected manual is NOT in the list
        self.assertNotIn(rejected_manual, manuals)
        
        # Check that others ARE in the list
        self.assertIn(pending_manual, manuals)
        self.assertIn(approved_manual, manuals)

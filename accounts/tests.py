from accounts.models import UserProfile
from testing.testcases import TestCase


# Create your tests here.
class UserProfileTests(TestCase):

    def setUp(self):
        super(UserProfileTests, self).setUp()

    def test_profile_property(self):
        lisa = self.create_user('lisa')
        self.assertEqual(UserProfile.objects.count(), 0)
        profile = lisa.profile
        self.assertEqual(isinstance(profile, UserProfile), True)
        self.assertEqual(UserProfile.objects.count(), 1)

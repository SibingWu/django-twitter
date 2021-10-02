from friendships.models import Friendship
from friendships.services import FriendshipService
from testing.testcases import TestCase


# Create your tests here.
class FriendshipServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.lisa = self.create_user('lisa')
        self.emma = self.create_user('emma')

    def test_get_followings(self):
        user1 = self.create_user('user1')
        user2 = self.create_user('user2')
        for to_user in [user1, user2, self.emma]:
            Friendship.objects.create(from_user=self.lisa, to_user=to_user)
        FriendshipService.invalidate_following_cache(self.lisa.id)

        user_id_set = FriendshipService.get_following_user_id_set(self.lisa.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id, self.emma.id})

        Friendship.objects.filter(from_user=self.lisa, to_user=self.emma).delete()
        FriendshipService.invalidate_following_cache(self.lisa.id)
        user_id_set = FriendshipService.get_following_user_id_set(self.lisa.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id})
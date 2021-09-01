from testing.testcases import TestCase


# Create your tests here.
class CommentModelTests(TestCase):

    def test_comment(self):
        user = self.create_user(username='lisa')
        tweet = self.create_tweet(user=user)
        comment = self.create_comment(user=user, tweet=tweet)
        self.assertNotEqual(comment.__str__(), None)

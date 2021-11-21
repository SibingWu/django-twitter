from testing.testcases import TestCase


# Create your tests here.
class CommentModelTests(TestCase):

    def setUp(self):
        super(CommentModelTests, self).setUp()
        self.lisa = self.create_user('lisa')
        self.tweet = self.create_tweet(user=self.lisa)
        self.comment = self.create_comment(user=self.lisa, tweet=self.tweet)

    def test_comment(self):
        self.assertNotEqual(self.comment.__str__(), None)

    def test_like_set(self):
        # 自己给自己点赞
        self.create_like(user=self.lisa, target=self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        # 验证只能点赞一次
        self.create_like(user=self.lisa, target=self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        # 别人给自己点赞
        emma = self.create_user('emma')
        self.create_like(user=emma, target=self.comment)
        self.assertEqual(self.comment.like_set.count(), 2)

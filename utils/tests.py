from testing.testcases import TestCase
from utils.redis_client import RedisClient


class UtilsTests(TestCase):

    def setUp(self):
        self.clear_cache()

    def test_redis_client(self):
        # 测试 lpush 的效果
        conn = RedisClient.get_connection()
        conn.lpush('redis_key', 1)  # push在左侧
        conn.lpush('redis_key', 2)
        cached_list = conn.lrange('redis_key', 0, -1)  # 都是闭区间
        self.assertEqual(cached_list, [b'2', b'1'])

        RedisClient.clear()
        cached_list = conn.lrange('redis_key', 0, -1)
        self.assertEqual(cached_list, [])

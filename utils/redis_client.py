import redis
from django.conf import settings


class RedisClient:
    """
    Redis 是个服务，要访问一个服务的代码，叫做 Client
    """
    conn = None  # 类变量

    @classmethod
    def get_connection(cls):
        # 使用 singleton 模式，全局只创建一个 connection
        # request -> web server starts 1 process -> response
        # 一次 request 可能有多次 redis get/redis set
        # 只建立一次 connection，否则效率太慢
        # response 回去后，process 结束，conn会到 None
        if cls.conn:
            return cls.conn
        cls.conn = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
        )
        return cls.conn

    @classmethod
    def clear(cls):
        # clear all keys in redis, for testing purpose
        if not settings.TESTING:
            raise Exception('You can not flush redis in production environment')
        conn = cls.get_connection()
        conn.flushdb()

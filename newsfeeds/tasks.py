from celery import shared_task

from friendships.services import FriendshipService
from newsfeeds.constants import FANOUT_BATCH_SIZE
from utils.time_constants import ONE_HOUR


@shared_task(routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(tweet_id, created_at, follower_ids):
    # import 写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService

    batch_params = [
        {'user_id': follower_id, 'created_at': created_at, 'tweet_id': tweet_id}
        for follower_id in follower_ids
    ]

    # 一次性写入
    newsfeeds = NewsFeedService.batch_create(batch_params)
    return '{} newsfeeds created'.format(len(newsfeeds))

    # 其实若是一个 1kw 粉丝的博主发了一个 144字节的 tweet，
    # 如果把整个 tweet 去 fan out 到 1kw 粉丝中，会给 redis 的内存带来 1G 的耗费
    # 可进一步优化：在 newsfeed cache 中，不直接存储整个 tweet，而是只存 tweet id
    # 即不是把整个 newsfeed push 进 cache，而是只是 push 有哪些 id
    # 但这里可以不优化的原因：newsfeed 在 serialize 时，
    # 只有 user_id，tweet_id，和 created_at，并没有整条 tweet

    # 本质优化方法：对于明星用户，不要用 push model，而要用 pull model


@shared_task(routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(tweet_id, created_at, tweet_user_id):
    # import 写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService

    # 将推给自己的 Newsfeed 率先创建，确保自己能最快看到
    NewsFeedService.create(
        user_id=tweet_user_id,
        tweet_id=tweet_id,
        created_at=created_at,
    )

    # 在具体的 async task 中进行拆分，拆成一个个小的 async task

    # 获得所有的 follower ids，按照 batch size 拆分开
    follower_ids = FriendshipService.get_follower_ids(tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        # 拆成小的async task
        fanout_newsfeeds_batch_task.delay(tweet_id, created_at, batch_ids)
        index += FANOUT_BATCH_SIZE

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1,
    )

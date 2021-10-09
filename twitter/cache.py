# memcached
FOLLOWINGS_PATTERN = 'followings:{user_id}'
# 通常会把 user_id 作为外键放在很多表单中，而不会把 user profile id 作为外键
USER_PROFILE_PATTERN = 'userprofile:{user_id}'

# redis
USER_TWEETS_PATTERN = 'user_tweets:{user_id}'

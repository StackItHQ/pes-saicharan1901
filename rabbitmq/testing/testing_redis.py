import redis

try:
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r.ping()
    print("Redis is connected!")
except redis.ConnectionError:
    print("Failed to connect to Redis.")

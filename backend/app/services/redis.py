import redis
from app.core.config import settings

class RedisService:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client = redis.from_url(self.redis_url, decode_responses=True)

    def get_client(self):
        return self.client

    def enqueue_task(self, queue_name: str, task_data: str):
        self.client.rpush(queue_name, task_data)

    def dequeue_task(self, queue_name: str):
        return self.client.blpop(queue_name, timeout=1)

redis_service = RedisService()

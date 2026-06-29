from celery import Celery

from app.core.config import settings



import os

# Force Celery broker/results to respect runtime env (Windows/Docker differences).
_redis_url = os.getenv("REDIS_URL", settings.REDIS_URL)

print(f"[celery_app] REDIS_URL resolved as: {_redis_url}")

celery_app = Celery(
    "knowledgehub",
    broker=_redis_url,
    backend=_redis_url,
    include=["app.tasks"],
)


celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

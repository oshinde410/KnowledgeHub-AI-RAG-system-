from celery import Celery

from app.core.config import settings

import os

# Force Celery broker/results to respect runtime env (Windows/Docker differences).
_redis_url = os.getenv("REDIS_URL", settings.REDIS_URL)
_result_backend_url = os.getenv("CELERY_RESULT_BACKEND", "")

print(f"[celery_app] REDIS_URL resolved as: {_redis_url}")
print(f"[celery_app] CELERY_RESULT_BACKEND resolved as: {_result_backend_url or '<none>'}")

celery_app = Celery(
    "knowledgehub",
    broker=_redis_url,
    backend=_result_backend_url or None,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_ignore_result=True,
)

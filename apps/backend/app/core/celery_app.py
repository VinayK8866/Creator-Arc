from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "creator_arc_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Autodiscover tasks from the workers tasks module
celery_app.autodiscover_tasks(["workers"])

# Optional celery configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

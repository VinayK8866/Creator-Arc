import os
import sys

# Ensure worker can find app module and tasks
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.join(root_dir, "apps", "backend")

if backend_dir not in sys.path:
    sys.path.append(backend_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import the configured celery app
from app.core.celery_app import celery_app

# Force import of tasks so they register with Celery
import workers.tasks.media_tasks
import workers.tasks.youtube_tasks
import workers.tasks.rewriter_tasks

if __name__ == "__main__":
    celery_app.start()

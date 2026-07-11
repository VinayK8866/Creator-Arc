FROM python:3.11-slim

WORKDIR /code

# Copy requirements from the backend since workers need to load DB modules
COPY ./apps/backend/requirements.txt /code/backend_requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/backend_requirements.txt

COPY . /code

CMD ["celery", "-A", "workers.main", "worker", "--loglevel=info"]

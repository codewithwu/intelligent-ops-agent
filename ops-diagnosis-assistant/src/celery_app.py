import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Celery配置
celery_app = Celery(
    'ops_diagnosis',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=['src.tasks.diagnosis_tasks']
)

# Celery配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5分钟超时
    task_soft_time_limit=240,  # 4分钟软超时
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,  # 每个worker处理100个任务后重启
)

# 自动发现任务
celery_app.autodiscover_tasks()

if __name__ == '__main__':
    celery_app.start()